
import os
from google.appengine.ext import db
import webapp2
import jinja2
import cgi
import re
import random
import string
import hashlib
from xml.dom import minidom
import urllib2
import art_module
import url_module
import user_module
import blog_module


''' setup template path using jinja '''

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),
                               autoescape=True)


def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)


def make_salt():
    return ''.join(random.choice(string.letters) for x in xrange(5))


def make_hash(name, hash_val, salt=''):
    if salt == '':
        salt = make_salt()
    h = hashlib.sha256(name + hash_val + salt).hexdigest()
    return '%s|%s' % (h, salt)


def pull_userdata_from_db(username):
    userdata = db.GqlQuery('SELECT * FROM UserDB WHERE username=:1 limit 1', username).get()
    return userdata


def is_valid_hash_input(name, check_input, hash_val):
    ''' determines if check_input and hash_val match '''
    salt = hash_val.split('|')[1]
    if make_hash(name, check_input, salt) == hash_val:
        return True
    else:
        return False


def escape_html(s):
    return cgi.escape(s, quote=True)


''' functions to validate input fields '''

def valid_username(username):
    USER_RE = re.compile(r'^[a-zA-Z0-9_-]{3,20}$')
    return username and USER_RE.match(username)


def valid_password(password):
    PASS_RE = re.compile(r'^.{3,20}$')
    return password and PASS_RE.match(password)


def valid_email(email):
    EMAIL_RE = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
    return not email or EMAIL_RE.match(email)


def username_available(username):
    userdata = pull_userdata_from_db(username)
    if not userdata:
        return True
    else:
        return False


IP_URL = 'http://api.hostip.info/?='

def get_coords(ip):
    '''
    takes in an ip address
    returns GeoPt(lat, lon) if there are coordinates
    using'http://api.hostip.info/?='
    '''
    url = IP_URL + ip
    content = None
    try:
        content = urllib2.urlopen(url).read()
    except URLError:
        return

    if content:
        dom1 = minidom.parseString(content)

    for node in dom1.getElementsByTagName('gml:coordinates'):
        coords = (node.toxml())
        trim = len('<gml:coordinates>')
        lon, lat = string.split(coords[trim:-1*(trim+1)], ',')
        return db.GeoPt(lat, lon)


''' functions to shorten URLs '''

def add_http(url_long):
    if not (url_long.startswith('http://') or url_long.startswith('https://')):
        url_long = 'http://' + url_long
    return url_long


def return_short_url(url_long):
    url_long = add_http(url_long)
    urldata = check_for_url_long(url_long)
    if not urldata:
        return make_url_short(url_long)
    else:
        return urldata


def pull_urldata_from_db(url_long='', url_short=''):
    if url_long:
        urldata = db.GqlQuery('SELECT * FROM Url WHERE url_long=:1 limit 1',
                              url_long).get()
        return urldata
    elif url_short:
        urldata = db.GqlQuery('SELECT * FROM Url WHERE url_short=:1 limit 1',
                              url_short).get()
        return urldata
    else:
        return


def add_url_to_db(url_long, url_short):
    url_module.Url(url_long=url_long, url_short=url_short, use_count=1).put()


def check_for_url_long(url_long):
    urldata = pull_urldata_from_db(url_long)
    if urldata:
        urldata.use_count = urldata.use_count + 1
        urldata.put()
        return urldata.url_short
    else:
        return


def check_for_url_short(url_short):
    urldata = pull_urldata_from_db(url_short)
    if not urldata:
        return True
    else:
        return False


def make_url_short(url_long):
    url_short = ''.join(random.choice(string.letters) for x in xrange(6))
    if check_for_url_short(url_short):
        add_url_to_db(url_long, url_short)
        return url_short
    else:
        make_url_short(url_long)


class Handler(webapp2.RequestHandler):
    ''' Handler class with helper methods
    for rendering pages & managing cookies '''

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        return render_str(template, **params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        username = self.request.cookies.get('user')
        userid = self.request.cookies.get('userid')
        hash_val = self.request.cookies.get('hash')

        return cookie_val and is_valid_hash_input(username,
                                                  userid,
                                                  hash_val)

    def set_cookie(self, cookie_username, cookie_user_id, cookie_hash_id):
        self.response.headers.add_header('Set-Cookie',
                                         'user=' + cookie_username +
                                         '; Path=/')
        self.response.headers.add_header('Set-Cookie',
                                         'userid=' + cookie_user_id +
                                         '; Path=/')
        self.response.headers.add_header('Set-Cookie',
                                         'hash=' + cookie_hash_id +
                                         '; Path=/')

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and user_module.UserDB.get_by_id(int(uid))


# render index page
class Index(Handler):
    def get(self):
        self.write('Hello! Nothing to see here')


# render newest 10 blog posts
class BlogPage(Handler):
    def get(self):
        entries = db.GqlQuery('SELECT * FROM Blog ORDER BY created DESC LIMIT 10')
        self.render('front.html', entries=entries)


# page to post new blog entries
class NewPost(Handler):
    def get(self):
        self.render('newpost.html')

    def post(self):
        subject = self.request.get('subject')
        content = self.request.get('content')

        if subject and content:
            new_post = blog_module.Blog(subject=subject, content=content)
            new_post.put()
            new_post_id = new_post.key().id()
            self.redirect('/blog/%s' % new_post_id)

        else:
            error = 'We need both a subject and some content!'
            self.render('newpost.html',
                        subject=subject,
                        content=content,
                        error=error)


# permalink for blog entries
class PostPage(Handler):
    def get(self, post_id=''):
        post_id = int(post_id)
        display_post = blog_module.Blog.get_by_id(post_id)

        if not display_post:
            self.write('This is not a real page, 4-oh-4')
            self.response.set_status(404)
            return

        self.render('blog-post.html', display_post=display_post)


# ASCII art page
class AsciiPage(Handler):
    def render_front(self, title='', art='', error=''):
        arts = db.GqlQuery('SELECT * FROM Art ORDER BY created DESC')
        self.render('ascii_front.html',
                    title=title,
                    art=art,
                    error=error,
                    arts=arts)

    def get(self):
        self.write(repr(get_coords(self.request.remote_addr)))
        return self.render_front

    def post(self):
        title = self.request.get('title')
        art = self.request.get('art')

        if title and art:
            a = art_module.Art(title=title, art=art)

            ## get map for ip:
            ## lookup user's coordinates from their IP
            # if we have coordinates, add them to the Art

            a.put()
            self.redirect('/ascii')

        else:
            error = 'we need both a title and some artwork!'
            self.render_front(title, art, error)


# site signup page
class SignupPage(Handler):
    def get(self):
        self.render('signup-form.html')

    def post(self):
        user_username = self.request.get('username')
        user_password = self.request.get('password')
        user_verify = self.request.get('verify')
        user_email = self.request.get('email')
        params = dict(username=user_username,
                      email=user_email)
        have_error = False

        if not (user_password == user_verify):
            params['user_verror'] = "Your passwords didn't match."
            have_error = True

        if not (valid_password(user_password)):
            params['user_perror'] = "That wasn't a valid password."
            have_error = True

        if not (valid_username(user_username)):
            params['user_uerror'] = "That's not a valid username."
            have_error = True

        if not (user_email == '' or valid_email(user_email)):
            params['user_eerror'] = "That's not a valid email."
            have_error = True

        if not username_available(user_username):
            params['user_uerror'] = "That username isn't available"
            have_error = True

        if have_error:
            self.render('signup-form.html', **params)
        else:
            hash_pw = make_hash(user_username, user_password)
            new_user = user_module.UserDB(username=user_username,
                                          hash_pw=hash_pw)
            new_user.put()
            user_id = str(new_user.key().id())
            hash_id = make_hash(user_username, user_id)
            self.set_cookie(str(user_username), str(user_id), str(hash_id))
            self.redirect('/welcome')


# site login page
class LoginPage(Handler):
    def get(self):
        self.render('login-form.html')

    def post(self):
        user_username = self.request.get('username')
        user_password = self.request.get('password')

        params = dict(username=user_username)
        have_error = False

        if not (valid_password(user_password)):
            params['user_perror'] = 'Invalid login'
            have_error = True

        if not (valid_username(user_username)):
            params['user_perror'] = 'Invalid login'
            have_error = True

        if not have_error:
            userdata = pull_userdata_from_db(user_username)

            if not userdata:
                params['user_perror'] = 'Invalid login'
                have_error = True

            else:
                hash_pw = userdata.hash_pw
                if not is_valid_hash_input(user_username,
                                           user_password,
                                           hash_pw):
                    params['user_perror'] = 'Invalid login'
                    have_error = True

        if have_error:
            self.render('login-form.html', **params)
        else:
            # update session value hash in cookie & db
            user_id = str(userdata.key().id())
            hash_id = make_hash(user_username, user_id)
            self.set_cookie(str(user_username), str(user_id), str(hash_id))
            self.redirect('/welcome')


# welcome after logging in
class WelcomePage(Handler):
    def get(self):
        username = self.request.cookies.get('user')
        userid = self.request.cookies.get('userid')
        hash_val = self.request.cookies.get('hash')

        if valid_username(username) and is_valid_hash_input(username,
                                                            userid,
                                                            hash_val):
            self.render('welcome.html', username=username)
        else:
            self.redirect('/signup')


#site logout page
class LogoutPage(Handler):
    def get(self):
        # clear cookie values
        self.set_cookie('', '', '')
        self.redirect('/signup')


# URL shortner page
class URLPage(Handler):
    def write_form(self, error='', url_in='', url_out=''):
        self.render('short-url.html',
                    error=error,
                    url_in=escape_html(url_in),
                    url_out='')

    def get(self):
        self.write_form()

    def post(self, error='', url_in=''):
        user_url_in = self.request.get('url_in')

        if user_url_in == '':
            self.write_form('Please enter a valid URL into the input box',
                            user_url_in)
        else:
            url_short = return_short_url(user_url_in)
            url_out = 'http://pogiralt.appspot.com/' + url_short
            self.render('short-url.html',
                        error='',
                        url_in=user_url_in,
                        url_out=url_out)


# short url redirector handling
class Redirector(Handler):
    def get(self, url_in=''):
        # try:
        urldata = pull_urldata_from_db(url_short=url_in)

        if not urldata:
            self.write('This is not a real page, 4-oh-4')
            self.response.set_status(404)
            return

        display_url = urldata.url_long
        self.redirect(str(display_url))


app = webapp2.WSGIApplication([('/', Index),
                               ('/welcome', WelcomePage),
                               ('/blog', BlogPage),
                               ('/blog/newpost', NewPost),
                               ('/blog/(\d+)', PostPage),
                               ('/ascii', AsciiPage),
                               ('/signup', SignupPage),
                               ('/login', LoginPage),
                               ('/logout', LogoutPage),
                               ('/shorten', URLPage),
                               ('/(\w+)', Redirector)
                               ], debug=True)
