from google.appengine.ext import db


class Art(db.Model):
    ''' model for blog ascii art '''
    title = db.StringProperty(required=True)
    art = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    coords = db.GeoPtProperty()
