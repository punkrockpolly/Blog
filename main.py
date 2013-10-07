
import os
import urllib

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import ndb

import webapp2
import jinja2


template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), 
                                autoescape = True)


class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
    
    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)
    
    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

class Blog(db.Model):
    subject = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now_add = True)

    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("newpost.html", p = self)

class MainPage(Handler):
    def render_front(self):
    	entries = db.GqlQuery("SELECT * FROM Blog ORDER BY created DESC LIMIT 10")
        self.render("front.html", entries=entries)
    
    def get(self):
        self.render_front()

    #def post(self):
    
    
class NewPost(Handler):
    def render_front(self, subject="", content="", error=""):
        self.render("newpost.html", subject=subject, content=content, error=error)
    
    def get(self):
        self.render_front()

    def post(self):
        subject = self.request.get("subject")
        content = self.request.get("content")

        if subject and content:
            new_post = Blog(subject = subject, content = content)
            new_post.put()
            new_post_id = new_post.key().id()
            self.redirect('/blog/%s' % new_post_id)

        else:
            error = "We need both a subject and some content!"
            self.render_front(subject, content, error)

class PostPage(Handler):
    def render_front(self, post_id=""):
        post_id = int(post_id)
        display_post = Blog.get_by_id(post_id)
        
        if not post:
            self.error(404)
            return

        self.render("postpage.html", display_post=display_post)

    def get(self, post_id=""):
        self.render_front(post_id)
    
    
app = webapp2.WSGIApplication([('/blog', MainPage), 
                               ('/blog/newpost', NewPost), 
                               ('/blog/(\d+)', PostPage),
                               ], 
                               debug=True)


