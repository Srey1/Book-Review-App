# Main python file!
from distutils.log import debug
import re
from flask import Flask, redirect, render_template, request, session, url_for, g
from models import *
from flask_sqlalchemy import SQLAlchemy
from passlib.hash import pbkdf2_sha256
import os
from werkzeug.utils import secure_filename
from functools import wraps
from sqlalchemy.pool import NullPool
import boto3, botocore


app = Flask(__name__)


allowed_files = ['png', 'jpg', 'jpeg']

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuring the pool size
app.config['SQLALCHEMY_POOL_SIZE'] = 50
app.config['SQLALCHEMY_MAX_OVERFLOW'] = 50
app.config['SQLALCHEMY_POOL_TIMEOUT'] = 10
app.config['SQLALCHEMY_POOL_RECYCLE'] = 3600

# Configuring the database
db = SQLAlchemy(app)

def login_required(func):
    '''
    Decorator function used to make sure people are logged in before accessing other pages
    '''
    @wraps(func)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for('index', next=request.url))
        return func(*args, **kwargs)
    return decorated

@app.route("/", methods=['GET', 'POST'])
def index():
    '''
        Login funtion used to log people in by searching the database for their account and confirming their password
    '''

    # Displaying the login template if the user wants to go to the login page
    if request.method == "GET":
        return render_template("login.html")
    else:
        # Getting the information the user entered
        username = request.form.get("username")
        password = request.form.get("password")
        # Making sure the information is filled
        if username == None or password == None or username == "" or password == "":
            return redirect("/")
        # Getting the user from the database based on the username
        current_user = Current_User(username, password)
        db.session.close()
        # Verifying users password user passlib
        if (current_user.verify()):
            # Checking if the user is a admin and rendering a different page if they are
            if username == "Admin":
                return redirect("/admin")
            return redirect("/main")
        # If the password is wrong then redirect them back to the login page
        return redirect("/")

@app.route("/logout", methods=['GET', 'POST'])
def logout():
    '''
        Method to delete user from session
    '''
    session.pop("user_id", None)
    return redirect(url_for("index"))


@app.route("/signup", methods=['GET', 'POST'])
def signup():
    '''
        Signup function used to add people to the database
    '''

    if request.method == "GET":
        return render_template("signup.html")
    else:
        # Getting the information the user entered
        username = request.form.get("username")
        password = request.form.get("password")
        check_password = request.form.get("check_password")
        name = request.form.get("email")
        # Creating an instance of the New_User Class using the information the user entered
        new = New_User(username, password, check_password, name)
        if new.set():
            return redirect("/main")
        else:
            print("Failed singup!")
        return render_template("signup.html")

s3 = boto3.client(
   "s3",
   aws_access_key_id=app.config['S3_KEY'],
   aws_secret_access_key=app.config['S3_SECRET']
)

def upload_file_to_s3(file, bucket_name, acl="public-read"):
    """
    Docs: http://boto3.readthedocs.io/en/latest/guide/s3.html
    A function that uploads the picture to amazon web servers where it is stored
    """
    # Error handling used to upload the file to amazon s3. 
    # The upload is done using the upload_fileobj method that comes from the s3 library imported
    # All required parameters are passed into the method
    try:
        s3.upload_fileobj(
            file,
            bucket_name,
            file.filename,
            ExtraArgs={
                "ACL": acl,
                "ContentType": file.content_type    #Set appropriate content type as per the file
            }
        )
    # If an error occurs print out the error message as outlined
    except Exception as e:
        print("Something Happened: ", e)
        return False
    return "{}{}".format(app.config["S3_LOCATION"], file.filename)
    
@app.route("/main", methods=['GET', 'POST'])
@login_required
def main():
    '''
        Method for the main page where users see the grid of books
    '''
    if request.method == "GET":
        # Getting all the information required
        names = []
        pictures = []
        names = Book.query.with_entities(Book.title).all()
        pictures = Book.query.with_entities(Book.image).all()
        bookID = Book.query.with_entities(Book.book_id).all()
        final_names = []
        final_pictures = []
        final_bookID = []
        db.session.close()
        # names, pictures,and bookID are 2D arrays in which each item is its own array. The following lines of code turn them into 1D arrays
        for i in names:
            for j in i:
                final_names.append(j)
        for i in pictures:
            for j in i:
                final_pictures.append(app.config['S3_LOCATION'] + j)
        for i in bookID:
            for j in i:
                final_bookID.append(j)

        length = len(names)
        # Rendering the main template while passing in the required information
        return render_template("main.html", names = final_names, pictures = final_pictures, length = length, id = final_bookID)
    else:
        form = request.form.get("chosen")
        # Perform the following operations if the user is searching for something
        if form == "search":
            book_title = request.form.get("search")
            if book_title == "":
                return redirect("/main")
            # Search for the book title within the books database
            books = Book.query.filter(Book.title.contains(book_title)).all()
            # books is a list of lists of each individual elements, so using list comprehension we convert it into a one dimensional list
            final_bookID = [i.book_id for i in books]
            final_pictures = [app.config['S3_LOCATION'] + i.image for i in books]
            final_names = [i.title for i in books]
            length = len(final_names)
            # Rendering the template main.html  but this time only displaying the books that were searched for
            return render_template("main.html", names = final_names, pictures = final_pictures, length = length, id = final_bookID)
        if form == "sort":
            # Do the following if the user wants to sort the books by their rating
            names = []
            pictures = []
            # Querying the database for the information needed
            names = Book.query.with_entities(Book.title).all()
            pictures = Book.query.with_entities(Book.image).all()
            bookID = Book.query.with_entities(Book.book_id).all()
            rating = Book.query.with_entities(Book.rating).all()
            final_names = []
            final_pictures = []
            final_bookID = []
            final_rating = []
            db.session.close()
            # names, pictures,bookID, and rating are 2D arrays in which each item is its own array. 
            # The following lines of code turn them into 1D arrays
            for i in names:
                for j in i:
                    final_names.append(j)
            for i in pictures:
                for j in i:
                    final_pictures.append(app.config['S3_LOCATION'] + j)
            for i in bookID:
                for j in i:
                    final_bookID.append(j)
            for i in rating:
                for j in i:
                    final_rating.append(j)

            # Calling the function parralel_sort(Created Below)
            parallel_sort(final_rating, [final_bookID, final_pictures, final_names])

            length = len(names)
            # Sending the user back to the main template just the arrays are sorted now so the books will display in order of highest rated to lowest rated
            return render_template("main.html", names = final_names, pictures = final_pictures, length = length, id = final_bookID)
        else:
            # If the user chooses a book to se more information do the following code:
            book = request.form.get("chosen")
            bookObject = Book.query.filter_by(book_id = book).first()
            info = Book_Information(bookObject.title, bookObject.author, bookObject.genre, bookObject.rating, bookObject.description, bookObject.pages, bookObject.grade, bookObject.image)
            average_rating = info.calculate_average()
            session["book"] = book
            return redirect(url_for('book_info'))
        
@app.route("/addBook", methods=['GET', 'POST'])
@login_required
def addBook():
    '''
        Method for the user to add a book
    '''
    if request.method == "GET":
        # Rendering the addBook template
        return render_template("addBook.html")
    else:
        # Getting the information entered
        title = request.form.get("title")
        author = request.form.get("author")
        genre = request.form.get("genre")
        rating = request.form.get("rating")
        pages = request.form.get("pages")
        grade = request.form.get("grade")
        description = request.form.get("description")
        # If the user did not enter some information then set that information to its default value
        if genre == "":
            genre = ""
        if pages == "":
            pages = 0
        if grade == "":
            grade = 0
        if description == "":
            description = ""
        # Using error-handling to see if they entered an integer page and not a string
        try:
            pages = int(pages)
            grade = int(grade)
        except ValueError:
            # If they did enter a string, a value error would occur so we should send them back to the add boook page
            return redirect("/addBook")
        
        # Getting the file they added, and uploading it to amazon AWS
        file = request.files['file']

        if not file:
            return redirect("/addBook")
        # Checking that the file exists and that it is of an allowed file type(jpeg, jpg, or png)
        if file and allowed_file(file.filename):
            file.filename = secure_filename(file.filename)
            upload = upload_file_to_s3(file, app.config["S3_BUCKET"]) 
            if upload == False:
                return redirect("/addBook")
            filename = secure_filename(file.filename)
        # Adding the new book to the database
        book = Book(person_id = session["user_id"], title = title, author = author, genre = genre, rating = rating, pages = pages, grade = grade, description = description, image = filename, like_count = 0)
        db.session.add(book)
        db.session.commit()

        return redirect("/main")
        
        
@app.route("/book_info", methods=['GET', 'POST'])
@login_required
def book_info():
    '''
        Method to get to the book information page
    '''
    if request.method == "GET":
        # Finding the book that was clicked on and displaying that page
        book = session["book"]
        # Getting the information from the database and running some basic calculations
        bookObject = Book.query.filter_by(book_id = book).first()
        # Creating a Book Information Object to run some basic calculations
        info = Book_Information(bookObject.title, bookObject.author, bookObject.genre, bookObject.rating, bookObject.description, bookObject.pages, bookObject.grade, bookObject.image)
        average_rating = info.calculate_average()
        liked1 = Likes.query.filter_by(book_id = book).all()
        person = User.query.filter_by(id = bookObject.person_id).first()
        comments = Comments.query.filter_by(book_id = book).all()
        final_comments = [i.comment for i in comments]
        names = []
        for i in comments:
            people = User.query.filter_by(id = i.person_id).first()
            names.append(people.name)
        length = len(final_comments)
        final_like = len(liked1)
        pages = info.pages
        if pages == 0:
            pages = "Unkown"
        return render_template("book_info.html", id = bookObject.book_id, 
        title = info.title, 
        author = info.author, 
        genre = info.genre,
        rating = info.rating, 
        description = info.description, 
        pages = pages, 
        grade = info.grade, 
        image = info.picture, 
        average = average_rating, 
        likes = final_like,
        person = person.name,
        comments = final_comments,
        length = length,
        names = names)
    else:
        # Checking if the book was was liked
        form = request.form.get("add_like")
        if form[-1] == "a":
            id_book = request.form.get("add_like")
            id_book = id_book[0:-1]
            id_book = int(id_book)
            book = Book.query.filter_by(book_id = id_book).first()
            liked = Likes.query.filter_by(book_id = id_book).all()
            already_liked = False
            counter = 0
            # Checking if that person already liked the book
            for i in liked:
                if i.person_id == session["user_id"]:
                    already_liked = True
                    break
                counter += 1
            # If it is not liked then add that like to the database
            if not already_liked:
                db.session.commit()
                like = Likes(book_id = book.book_id, person_id = session["user_id"])
                db.session.add(like)
                db.session.commit()
            # If it is already liked by that person then delete that like from the database
            else:
                to_go = db.session.query(Likes).filter(Likes.like_id == liked[counter].like_id).first()
                db.session.delete(to_go)
                db.session.commit() 
            return redirect("/book_info")
        else:
            # The user wants to add a comment so send it to the comments database
            id_book = int(request.form.get("add_like"))
            session["book_id"] = id_book
            return redirect(url_for("comment"))


@app.route("/comment", methods=['GET', 'POST'])
@login_required
def comment():
    '''
        Method to get to the comments page and add a comment
    '''
    if request.method == "GET":
        # Displaying the comments page
        return render_template("comment.html", id = session["book_id"])
    else:
        # Getting the comment the user entered and adding it to the comments table
        id_book = int(request.form.get("book_id"))
        person_id = session["user_id"]
        comment1 = request.form.get("comment1")
        comment = Comments(book_id = id_book, person_id = person_id, comment = comment1)
        db.session.add(comment)
        db.session.commit()
        return redirect("/main")

        

@app.route("/history", methods=['GET', 'POST'])
@login_required
def history():
    '''
        Method to get to the history page and delete a book
    '''
    if request.method == "GET":
        # Getting all the data to show the history page
        books = Book.query.filter_by(person_id = session["user_id"]).all()
        ratings = [i.rating for i in books]
        pictures = [app.config['S3_LOCATION'] + i.image for i in books]
        titles = [i.title for i in books]
        ids = [i.book_id for i in books]
        db.session.close()
        length = len(titles)
        return render_template("history.html", ratings = ratings, pictures = pictures, titles = titles, length = length, ids = ids)
    if request.method == "POST":
        # Getting the id of the book the user wants to delete
        id = int(request.form.get("id"))
        # Finding all the likes givven to that book
        likes = db.session.query(Likes).filter(Likes.book_id == id).all()
        # Finding all the comments given to that book
        comments = db.session.query(Comments).filter(Comments.book_id == id).all()
        # Deleting all the likes givven to that book
        for i in comments:
            db.session.delete(i)
            db.session.commit() 
        # Deleting all the comments given to that book
        for i in likes:
            db.session.delete(i)
            db.session.commit() 
        
        to_go = db.session.query(Book).filter(Book.book_id == id).first()
        db.session.delete(to_go)
        db.session.commit() 
    
        return redirect("/history")

@app.route("/statistics", methods=["GET"])
@login_required
def statistics():
    '''
        Method to get to the statistics page and view all statistics through the calculations done
    '''
    if request.method == "GET":
        # Gathering all the data required for the statistics page and then showing the data
        books = Book.query.filter_by(person_id = session["user_id"]).all()
        # Creating a student object to run some calculations within the student class
        student = Student(books)
        db.session.close()
        return render_template("statistics.html", 
        books_reviewed = student.books_read(), 
        average_rating = student.average_rating_given(), 
        pages_read = student.pages_read(),
        likes_given = student.likes_given(),
        likes_recieved = student.likes_recieved(),
        genres = student.genre_read(),
        authors = student.authors_read())



def allowed_file(name):
    # Making sure the file type is allowed (jpg, png, or jpeg )
    return '.' in name and name.rsplit('.', 1)[1].lower() in allowed_files

@app.route("/admin", methods=['GET', 'POST'])
@login_required
def admin():
    '''
        Method to render the admin page and allow the admin to delete any book
    '''
    if request.method == "GET":
        # Initializing the admin object and verfying they are an Admin
        person = Admins(session["user_id"])
        if not person.verify():
            return redirect(url_for("main"))
        # Getting all the data required to show the page
        books = Book.query.all()
        ratings = [i.rating for i in books]
        pictures = [app.config['S3_LOCATION'] + i.image for i in books]
        titles = [i.title for i in books]
        ids = [i.book_id for i in books]
        length = len(titles)
        return render_template("admin.html", ratings = ratings, pictures = pictures, titles = titles, length = length, ids = ids)
    if request.method == "POST":
        id = int(request.form.get("id"))
        # Initializing an Admin object and deleting any book based on the method it has
        person = Admins(session["user_id"])
        person.delete(id)
        return redirect("/admin")

class Admins:
    def __init__(self, id):
        self.__id = id
    def verify(self):
        # The admin is at id 12. There is only one id 12 so there will only be one admin 
        return self.__id == 12
    def delete(self, id_book):
        # Method for the admin to delee any book
        likes = db.session.query(Likes).filter(Likes.book_id == id_book).all()
        comments = db.session.query(Comments).filter(Comments.book_id == id_book).all()
        for i in comments:
            db.session.delete(i)
            db.session.commit() 
        for i in likes:
            db.session.delete(i)
            db.session.commit() 
        
        to_go = db.session.query(Book).filter(Book.book_id == id_book).first()
        db.session.delete(to_go)
        db.session.commit() 

class Current_User:
    def __init__(self, username, password):
        self.__username = username
        self.__password = password
    def verify(self):
        # Making sure that the username filled out the password and username field
        if self.__username == None or self.__password == None:
            return False
        
        # Checking if the user is already in the database
        user = User.query.filter_by(username = self.__username).first()
        # If they are then return false
        if (user == None):
            return False
        
        # If they are not then unhash their password and check if it matches the one they entered. If they do then let the user login
        if (pbkdf2_sha256.verify(self.__password, user.password)):
            session["user_id"] = user.id
            return True
        return False
        

class Book_Information:
    def __init__(self, title, author, genre, rating, description, pages, grade, picture):
        self.title = title
        self.author = author
        self.genre = genre
        self.rating = rating
        self.description = description
        self.pages = pages
        self.grade = grade
        self.picture = picture
        self.picture = app.config['S3_LOCATION'] + picture
    def calculate_average(self):
        # Getting the average of that book
        books = Book.query.filter_by(title = self.title).all()
        final_rating = []
        for i in books:
            final_rating.append(i.rating)
        return sum(final_rating)/len(final_rating)



class New_User:
    def __init__(self, username, password, check_password, name):
        # Initializing the Variables
        self.__username = username
        self.__password = password
        self.__check_password = check_password
        self.__name = name
    def set(self):
        # Ensure all information was submitted
        if self.__username == None or self.__password == None or self.__check_password == None or self.__name == None:
            return False
        # Make sure the school domain name is in the password
        if "@student.aisb.hu" not in self.__username and "@aisb.hu" not in self.__username:
            return False
        # Make sure password is equal to the password confirmation
        elif self.__password != self.__check_password:
            return False
        # Check if username already exists
        otheruser = User.query.filter_by(username = self.__username).first()
        if otheruser:
            return False
        # Create new user in database and hash their password
        hashed_password = pbkdf2_sha256.hash(self.__password)
        user = User(username = self.__username, password = hashed_password, name = self.__name)
        db.session.add(user)
        db.session.commit()
        session["user_id"] = user.id
        return True

class Student:
    def __init__(self, books):
        # Initializing the Private Variable books where books is an array of the books the student read
        self.__books = books
    def books_read(self):
        # Finding the number of books the student read
        return len(self.__books)
    def pages_read(self):
        # Calculating the number of pages the student read based on the number of pages in each book the reviewed
        return sum([i.pages for i in self.__books])
    def average_rating_given(self):
        # Finding the average rating of the book
        if len(self.__books) != 0:
            return round((sum([i.rating for i in self.__books]) / len(self.__books)), 1)
        else:
            return ""
    def likes_recieved(self):
        # Calculating the number of likes the book recieved 
        likes = 0
        for i in self.__books:
            # Querying the likes table to find how many times that persons book was liked
            current_likes = Likes.query.filter_by(book_id = i.book_id).all()
            likes += len(current_likes)
        return likes
    def likes_given(self):
        # Calculating how many likes that person gave by querying the "Like" table for all the times when that person liked the book
        liked = Likes.query.filter_by(person_id = session["user_id"]).all()
        return len(liked)
    def genre_read(self):
        # Calculating how many different genres that person read
        done = []
        for i in self.__books:
            # Making sure that that this genre has not already been counted
            if i.genre not in done:
                done.append(i.genre)
        return len(done)
    def authors_read(self):
        # Calculating how many different authors that person read
        done = []
        for i in self.__books:
            # Making sure that that this author has not already been counted
            if i.author not in done:
                done.append(i.author)
        return len(done)

def parallel_sort(array, others):
    # Method to sort the list of books based on rating using a bubble_sort algorithm
    # It will sort  the array named "others" parralelly to the array named "array"
    # Using a bubble sort  type of algorithm that will be used to sort both arrays based of one
    swapped = False
    for i in range(len(array)):
        for j in range(len(array) - i - 1):
            if array[j] < array[j + 1]:
                swapped = True
                array[j + 1], array[j] = array[j], array[j + 1]
                for y in others:
                    y[j + 1], y[j] = y[j], y[j + 1]
        # Break out if the sorting is complete
        if not swapped:
            return False

if __name__ == '__main__':
    app.run( )