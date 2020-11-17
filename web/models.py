from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

# init SQLAlchemy so we can use it later in our models
db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
