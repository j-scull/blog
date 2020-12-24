from threading import Thread
from flask_mail import Message
from app import mail
from flask import current_app


# set up local email server
# python -m smtpd -n -c DebuggingServer localhost:8025
# set MAIL_SERVER=localhost
# set MAIL_PORT=8025

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()



    