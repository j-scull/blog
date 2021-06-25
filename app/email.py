"""
Provides email support for the blog.
Cases where user's are emailed by the blog include:
- password reset requests
- user post download requests

An email server can be set up locally for test purposes using:
>> python -m smtpd -n -c DebuggingServer localhost:8025
>> export MAIL_SERVER=localhost
>> export MAIL_PORT=8025

To set up a gmail server do the following:
>> export MAIL_SERVER=stmp.googlemail.com
>> export MAIL_PORT=587
>> export MAIL_USE_TLS=1
>> export MAIL_USERNAME=<gmail address>
>> export MAIL_PASSWORD=<password>

"""

from threading import Thread
from flask_mail import Message
from app import mail
from flask import current_app




def send_async_email(app, msg):
    """
    Sends an email
    --------------
    Parameters:
    app - the app
    msg - the Message object to be sent
    """
    with app.app_context():
        mail.send(msg)


def send_email(subject, sender, recipients, text_body, html_body, 
               attachments=None, sync=False):
    """
    Sends an email - sets up a thread to send the email asychronously
    -----------------------------------------------------------------
    Parameters:
    subject - the email subject
    sender - the sender of the email
    recipients - the recipients of the email
    text_body - the email content in txt
    html_body - the email content in html
    attachments - email attachments
    sync - if True, sends the email synchronously, otherwise sends asynchronously
    """
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    if attachments:
        for attachment in attachments:
            msg.attach(*attachment)
    if sync:
        mail.send(msg)
    Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()
