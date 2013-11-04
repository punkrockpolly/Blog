from google.appengine.ext import db


## model for url db
class Url(db.Model):
    url_long = db.StringProperty(required=True)
    url_short = db.StringProperty(required=True)
    use_count = db.IntegerProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
