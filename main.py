
import os
from google.appengine.ext import db
import webapp2
import jinja2
import cgi
import re
import random
import string
import hashlib


## setup template path using jinja

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),
                               autoescape=True)


def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)


def render_post(response, post):
    response.out.write('<b>' + post.subject + '</b><br>')
    response.out.write(post.content)


## Handler class with helper methods for rendering pages
class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        return render_str(template, **params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))


class Index(Handler):
    def get(self):
        self.write('Hello! Nothing to see here')


## model for blog entries
class Blog(db.Model):
    subject = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    last_modified = db.DateTimeProperty(auto_now_add=True)

    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("post.html", new_post=self)


## model for blog ascii art
class Art(db.Model):
    title = db.StringProperty(required=True)
    art = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)


## model for users
class UserDB(db.Model):
    username = db.StringProperty(required=True)
    hash_pw = db.StringProperty(required=True)
    join_date = db.DateTimeProperty(auto_now_add=True)


class BlogPage(Handler):
    def get(self):
        entries = db.GqlQuery("SELECT * FROM Blog ORDER BY created DESC LIMIT 10")
        self.render("front.html", entries=entries)


class NewPost(Handler):
    def get(self):
        self.render("newpost.html")

    def post(self):
        subject = self.request.get("subject")
        content = self.request.get("content")

        if subject and content:
            new_post = Blog(subject=subject, content=content)
            new_post.put()
            new_post_id = new_post.key().id()
            self.redirect('/blog/%s' % new_post_id)

        else:
            error = "We need both a subject and some content!"
            self.render("newpost.html", subject=subject, content=content, error=error)


class PostPage(Handler):
    def get(self, post_id=""):
        post_id = int(post_id)
        display_post = Blog.get_by_id(post_id)

        if not display_post:
            self.error(404)
            return

        self.render("postpage.html", display_post=display_post)


class AsciiPage(Handler):
    def render_front(self, title="", art="", error=""):
        arts = db.GqlQuery("SELECT * FROM Art ORDER BY created DESC")
        self.render("ascii_front.html", title=title, art=art, error=error, arts=arts)

    def get(self):
        self.render_front()

    def post(self):
        title = self.request.get("title")
        art = self.request.get("art")

        if title and art:
            a = Art(title=title, art=art)
            a.put()
            self.redirect("/ascii")

        else:
            error = "we need both a title and some artwork!"
            self.render_front(title, art, error)


def make_salt():
    return ''.join(random.choice(string.letters) for x in xrange(5))


def make_pw_hash(name, pw, salt=""):
    if salt == "":
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (h, salt)


## determines if pw and hash match
def is_valid_pw(name, pw, h):
    salt = h.split(',')[1]
    if make_pw_hash(name, pw, salt) == h:
        return True
    else:
        return False


def escape_html(s):
    return cgi.escape(s, quote=True)


## functions to validate input fields

def valid_username(username):
    USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
    return USER_RE.match(username)


def valid_password(password):
    PASS_RE = re.compile(r"^.{3,20}$")
    return PASS_RE.match(password)


def valid_email(email):
    EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")
    return EMAIL_RE.match(email)


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

        if not (user_email == "" or valid_email(user_email)):
            params['user_eerror'] = "That's not a valid email."
            have_error = True

        if have_error:
            self.render('signup-form.html', **params)
        else:
            h = make_pw_hash(user_username, user_password)
            new_user = UserDB(username=user_username, hash_pw=h)
            new_user.put()
            cookie_value = str(user_username)
            self.response.headers.add_header('Set-Cookie', 'user=' + cookie_value + '; Path=/')
            self.redirect('/welcome')


class LoginPage(Handler):
    def get(self):
        self.render('login-form.html')

    def post(self):
        user_username = self.request.get('username')
        user_password = self.request.get('password')

        params = dict(username=user_username)
        have_error = False

        if not (valid_password(user_password)):
            params['user_perror'] = "Invalid login"
            have_error = True

        if not (valid_username(user_username)):
            params['user_perror'] = "Invalid login"
            have_error = True

        if not have_error:
            userdata = db.GqlQuery("SELECT * FROM UserDB WHERE username=:1 limit 1", user_username)
            userdata = userdata.get()
            hash_pw = userdata.hash_pw

            if not userdata:
                params['user_perror'] = "Invalid login"
                have_error = True

            if not is_valid_pw(user_username, user_password, hash_pw):
                params['user_perror'] = "Invalid login"
                have_error = True

        if have_error:
            self.render('login-form.html', **params)
        else:
            cookie_value = str(user_username)

            self.response.headers.add_header('Set-Cookie', 'user=' + cookie_value + '; Path=/')
            self.redirect('/welcome')


class LogoutPage(Handler):
    def get(self):
        cookie_value = ''
        self.response.headers.add_header('Set-Cookie', 'user=' + cookie_value + '; Path=/')
        self.redirect('/signup')


class WelcomePage(Handler):
    def get(self):
        username = self.request.cookies.get('user')
        if valid_username(username):
            self.render('welcome.html', username=username)
        else:
            self.redirect('/signup')


app = webapp2.WSGIApplication([('/', Index),
                               ('/welcome', WelcomePage),
                               ('/blog', BlogPage),
                               ('/blog/newpost', NewPost),
                               ('/blog/(\d+)', PostPage),
                               ('/ascii', AsciiPage),
                               ('/signup', SignupPage),
                               ('/login', LoginPage),
                               ('/logout', LogoutPage),
                               ], debug=True)
