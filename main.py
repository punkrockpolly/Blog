
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
    #post_id = db.key().id()
	created = db.DateTimeProperty(auto_now_add = True)

class MainPage(Handler):
    def render_front(self, subject="", content="", error=""):
    	entries = db.GqlQuery("SELECT * FROM Blog "
                            "ORDER BY created DESC ")
        self.render("front.html", subject=subject, content=content, error=error, entries=entries)
    
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
    
    
class NewPost(Handler):
    def render_front(self, subject="", content="", error=""):
        self.render("front.html", subject=subject, content=content, error=error)
    
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
    
    
app = webapp2.WSGIApplication([('/blog', MainPage), ('/blog/newpost', NewPost)], debug=True)


