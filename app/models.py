"""
Defines the database models for the blog
"""

from hashlib import md5
from app import login, db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from time import time
from flask_login import UserMixin
import jwt
from flask import current_app
from app.search import add_to_index, remove_from_index, query_index
import json
import redis
import rq



# Create followers table - seconadary association table used in User class
followers = db.Table('followers', 
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

class User(UserMixin, db.Model):
    """
    Represents and provides the functionality for a user of the blog
    """
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    # author is used to attribute posts to users
    # p = Post(body='Hello...', author=u)
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    tasks = db.relationship('Task', backref='user', lazy='dynamic')
    
    # set up many-to-many follower-followed relationship
    followed = db.relationship(
        'User', 
        secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'),
        lazy='dynamic'
    )
    messages_sent = db.relationship('Message',
                                    foreign_keys='Message.sender_id',
                                    backref='author', lazy='dynamic')

    messages_received = db.relationship('Message',
                                    foreign_keys='Message.recipient_id',
                                    backref='recipient', lazy='dynamic')
    
    last_message_read_time = db.Column(db.DateTime)
    
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')

    def set_password(self, password):
        """
        Generates and stores a password hash for a user
        password: the password string entered by the user 
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """
        Validates a password entered by a user
        password: the password string entered by the user
        """
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        """
        Retruns: a string representation of the User class
        """
        return '<User {}>'.format(self.username)

    def avatar(self, size):
        """
        Generate an Avatar for a user using Gravatar
        """
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(digest, size)
    
    def follow(self, user):
        """
        Follow another user
        """
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        """
        Unfollow a user
        """
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        """
        Checks if the current user if following another given user
        """
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0  

    def followed_posts(self):
        """
        Returns: the posts of all users followed by the current user along with the current user's posts
        """
        followed = Post.query.join(
                followers, (followers.c.followed_id == Post.user_id)).filter(  # join posts and followers where followed_id = user_id 
                followers.c.follower_id == self.id)                            # filter to get rows where only current user is follower
        own = Post.query.filter_by(user_id=self.id)                            # get the current user's own posts
        return followed.union(own).order_by(Post.timestamp.desc())             # order by time of posting

    def user_posts(self):
        """
        Returns: the current user's posts
        """
        return Post.query.filter_by(user_id=self.id) 
            
    def get_reset_password_token(self, expires_in=600):
        """
        Generates the resset password token using JSON Web Tokens
        expires_in: token expiration time - default is ten minutes
        """
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        """
        Validates the token sent with the reset password link
        """
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'], 
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

    def new_messages(self):
        """
        Returns: the number of unread messages
        """
        last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
        return Message.query.filter_by(recipient=self).filter(
            Message.timestamp > last_read_time).count()
        
    def add_notification(self, name, data):
        """
        Updates the number of new unread messages for a user
        name - the notification type e.g. unread_message_count
        data - the notification content - can be a single value e.g. the number of unread messages
        """
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return

    def launch_task(self, name, description, *args, **kwargs):
        """
        Submits a task to the RQ queue.
        -------------------------------
        Parameters
        name - the function name defined in app/tasks.py
        description - a description of the task to present to users
        -------------------------------
        Returns
        A task object.
        """
        rq_job = current_app.task_queue.enqueue('app.tasks.' + name, self.id, 
                                                *args, **kwargs)
        task = Task(id=rq_job.get_id(), name=name, description=description, user=self)
        db.session.add(task)
        return task

    def get_tasks_in_progress(self):
        """
        Returns: any tasks in progress belonging to the user.
        """
        return Task.query.filter_by(user=self, complete=False).all()

    def get_task_in_progress(self, name):
        """
        Returns: a given task belonging to the user.
        """
        return Task.query.filter_by(name=name, user=self, complete=False).first()
        



class SearchableMixin(object):
    """
    Integrates Searching with SQLAlchemy.
    Uses SQLAlchemy events to keep the search index in sync with the database.
    
    *Can be used with any Search service and database model, in this app it is
    used to bind the Post model to ElasticSearch.
    Index query functions for ElasticSearch are defined in search.py
    """

    @classmethod
    def search(cls, expression, page, per_page):
        """
        Searches the index for a given text string.
        -------------------------------------------
        Parameters:
        expression - the text string to search for
        page - the current page
        per_page - the number of results to display per page
        -------------------------------------------
        Returns:
        A list of objects matching the search criterea
        """
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        return cls.query.filter(cls.id.in_(ids)).order_by(   # ensure DB results 
            db.case(when, value=cls.id)), total

    @classmethod
    def before_commit(cls, session):
        """
        Saves changes that are made to the database before they are committed
        session - a connected session with the database
        """
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        """
        Adds any objects in _changes to the index after they are committed to the database
        session - a connected session with the database
        """
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        """
        Adds all objects inthe the database relation to the search index
        """
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)



db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)



class Post(SearchableMixin, db.Model):
    """
    Represents a post by a user
    """
    __searchable__ = ['body']                       # the body of a post is searchable
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    # use uniform timestamp, will be converted into users local times
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    language = db.Column(db.String(5))

    def __repr__(self):
        """
        Returns: a string representation  of the post
        """
        return '<Post {}>'.format(self.body)



@login.user_loader   # flask-login
def load_user(id):
    """
    Keeps track of a unique identifier for each user
    """
    return User.query.get(int(id))



class Message(db.Model):
    """
    Support private messages between users
    """
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        """
        Returns: a string representation of the message
        """
        return '<Message {}>'.format(self.body)



class Notification(db.Model):
    """
    Keeps track of notifications for all users
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text)

    def get_data(self):
        """
        Returns: the message associated with the notification
        """
        return json.loads(str(self.payload_json))



class Task(db.Model):
    """
    Keeps track of background jobs for each user
    """

    id = db.Column(db.String(36), primary_key=True) # job id as primary key
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    complete = db.Column(db.Boolean, default=False)

    def get_rq_job(self):
        """
        Checks if a job exists.
        -----------------------
        Returns
        The relevant job if it exists, otherwise returns None.
        """
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job

    def get_progress(self):
        """
        Reports on a job's progress.
        Assumes a non-existent job is 100% complete.
        Assumes that a job without meta is 0% complete.
        -----------------------------------------------
        Returns
        Job completion percentage [0, 100].
        """
        job = self.get_rq_job()
        return job.meta.get('progress', 0) if job is not None else 100