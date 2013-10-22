
import os

from google.appengine.ext import db

import webapp2
import jinja2


template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), 
                               autoescape=True)


def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)


class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        return render_str(template, **params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))


def render_post(response, post):
    response.out.write('<b>' + post.subject + '</b><br>')
    response.out.write(post.content)


class WelcomePage(Handler):
    def get(self):
        self.write('Hello!')


class Blog(db.Model):
    subject = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    last_modified = db.DateTimeProperty(auto_now_add=True)

    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("post.html", new_post=self)


class Art(db.Model):
    title = db.StringProperty(required=True)
    art = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)


class MainPage(Handler):
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


app = webapp2.WSGIApplication([('/', WelcomePage),
                               ('/blog', MainPage),
                               ('/blog/newpost', NewPost),
                               ('/blog/(\d+)', PostPage),
                               ('/ascii', AsciiPage),
                               ], debug=True)
