import datetime
import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_navigation import Navigation
from recurrent import RecurringEvent
from wtforms import Form, StringField, validators

from ConfigParser import SafeConfigParser, NoSectionError
from passlib.hash import sha256_crypt

app = Flask(__name__, static_folder='../static')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
nav = Navigation(app)

nav.Bar('top', [
    nav.Item('Home', 'home'),

])

# dialect+driver://username:password@host:port/database
try:
    """Parse the properties and use SQL Alchemy to connect to DB"""
    parser = SafeConfigParser()
    parser.read('../properties.ini')

    host = parser.get('aws-user-pw', 'host')
    user = parser.get('aws-user-pw', 'user')
    password = parser.get('aws-user-pw', 'password')
    port = parser.get('aws-user-pw', 'port')
    database = parser.get('aws-user-pw', 'todo-database')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://' + user + ':' + password + \
                                            '@' + host + ':' + port + '/' + database
except NoSectionError as err:
    print('You need the correct Properties file in your root directory')

db = SQLAlchemy(app)


class User(db.Model):
    """Object mapping of users"""
    id = db.Column(db.Integer, primary_key=True)
    firstName = db.Column(db.String(52), nullable=False)
    lastName = db.Column(db.String(52), nullable=False)
    email = db.Column(db.String(128), nullable=False)
    password = db.Column(db.String(256), nullable=False)


class Todo(db.Model):
    """Object mapping of todos"""
    id = db.Column(db.Integer, primary_key=True)
    dueDate = db.Column(db.TIMESTAMP, nullable=False)
    createdAt = db.Column(db.TIMESTAMP, nullable=False)
    createdBy = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=True)

    def __init__(self, id, dueDate, createdAt, createdBy, text):
        self.id = id
        self.dueDate = dueDate
        self.createdAt = createdAt
        self.createdBy = createdBy
        self.text = text


@app.route('/logout', methods=['GET'])
def logout():
    """Logout route for users"""
    response = redirect(url_for('login'))
    response.delete_cookie('email')
    response.delete_cookie('todo_cookie')
    return response



@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login route for users"""
    error = None
    if request.method == 'POST':
        email = request.form['email']
        pw = request.form['password']
        temp_user = User.query.filter_by(email=email).first()

        if not sha256_crypt.verify(pw, temp_user.password):
            error = 'Invalid Credentials. Please try again.'
        else:
            # session['logged_in'] = True
            # session['email'] = email
            response = redirect(url_for('home'))
            response.set_cookie('email', email)
            response.set_cookie('todo_cookie', email)
            return response
    return render_template('login.html', error=error)


@app.route('/', methods=['POST', 'GET'])
@app.route('/home', methods=['POST', 'GET'])
def home():
    """Home page for user's todos"""
    cookie = request.cookies.get('todo_cookie')
    if not cookie:
        return redirect(url_for('login'))
    else:
        cur_user = User.query.filter_by(email=request.cookies.get('email')).first()
        first_name = cur_user.firstName

        if request.method == 'POST':
            """Once a todo is added, we process and add it"""
            text = request.form['text']
            raw_due_time = request.form['duedate']

            # Natural language processing of date
            r = RecurringEvent(now_date=datetime.datetime.now())
            datetime_due_time = r.parse(raw_due_time)

            # Format the date for SQL to be happy
            sql_time_format = '%Y-%m-%d %H:%M:%S'
            created_at_time = datetime.datetime.strftime(datetime.datetime.now(), sql_time_format)
            due_time = datetime.datetime.strftime(datetime_due_time, sql_time_format)

            # Creating the to do for the add to db
            new_todo = Todo(None, due_time, created_at_time, cur_user.id, text)
            db.session.add(new_todo)
            db.session.commit()

        todos = Todo.query.filter_by(createdBy=cur_user.id).all()
        if todos is not None:
            f = '%B %d, %Y %I:%M %p'
            for todo in todos:
                todo.dueDateFormat = datetime.datetime.strftime(todo.dueDate, f)
                todo.createdAtFormat = datetime.datetime.strftime(todo.createdAt, f)

        return render_template(
            'main-page.html', todos=todos, first_name=first_name)


if __name__ == "__main__":
    app.secret_key = os.urandom(12)
    app.run()
