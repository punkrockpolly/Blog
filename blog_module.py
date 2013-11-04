from google.appengine.ext import db


## model for users
class UserDB(db.Model):
    username = db.StringProperty(required=True)
    hash_pw = db.StringProperty(required=True)
    join_date = db.DateTimeProperty(auto_now_add=True)
