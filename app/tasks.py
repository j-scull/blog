"""
Background job scripts.

Tasks need access to Flask-SQLAlchemy and Flask-Mail - it is necessary to add
a Flask application instance so thses can get their configuration.
"""
import sys
import time
import json
from rq import get_current_job
from app import db
from app.models import Task, User, Post
from flask import render_template
from app.email import send_email
from app import create_app

app = create_app()
app.app_context().push()


def _set_task_progress(progress):
    """
    Notifies the user of task progress.
    Update Task completion and user notification in the database.
    """
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.save_meta()
        task = Task.query.get(job.get_id())
        task.user.add_notification('task_progress', {'task_id': job.get_id(),
                                                     'progress': progress})
        if progress >= 100:
            task.complete = True
        db.session.commit()



def export_posts(user_id):
    """
    Sends a user an email containing all their posts to date.
    """
    try:
        
        # read user posts from database
        user = User.query.get(user_id)
        _set_task_progress(0)
        data = []
        i = 0
        total_posts = user.posts.count()
        for post in user.posts.order_by(Post.timestamp.asc()):
            data.append({'body': post.body,
                         'timestamp': post.timestamp.isoformat() + 'Z'}) # Z indicates UTC
            time.sleep(5) # sleep in order to test notifications
            i += 1
            _set_task_progress(i * 100 // total_posts)

        # send email to user
        send_email('[Microblog] Your blog posts',
                    sender=app.config['ADMINS'][0], recipients=[user.email],
                    text_body=render_template('email/export_posts.txt', user=user),
                    html_body=render_template('email/export_posts.html', user=user),
                    attachments=[('posts.json', 'application/json',
                                  json.dumps({'posts':data}, indent=4))],
                    sync=True)
    
    except:
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())
    
    finally:
        _set_task_progress(100)

