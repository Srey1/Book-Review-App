# Database Page
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(), unique=True, nullable=False)
    password = db.Column(db.String(), nullable=False)
    name = db.Column(db.String(), nullable=False)

class Book(db.Model):
    __tablename__ = 'books'
    book_id = db.Column(db.Integer, primary_key = True)
    person_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    title = db.Column(db.String(),nullable=True)
    author = db.Column(db.String(), nullable=True)
    genre = db.Column(db.String(), nullable=True)
    rating = db.Column(db.Float(), nullable=True)
    pages = db.Column(db.Integer, nullable=True)
    grade = db.Column(db.Integer, nullable=True)
    description = db.Column(db.String, nullable=True)
    image = db.Column(db.String())
    like_count = db.Column(db.Integer, nullable=True)

class Likes(db.Model):
    __tablename__ = 'likes'
    like_id = db.Column(db.Integer, primary_key = True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.book_id'))
    person_id = db.Column(db.Integer, db.ForeignKey('users.id'))

class Comments(db.Model):
    __tablename__ = 'comments'
    comment_id = db.Column(db.Integer, primary_key = True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.book_id'))
    person_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comment = db.Column(db.String(), nullable = False)

