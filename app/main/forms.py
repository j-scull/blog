"""
Provides forms for the main functionality of the blog,
i.e. editing profiles, posting, messaging and search
"""

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import ValidationError, DataRequired, Length
from app.models import User
from flask_babel import lazy_gettext as _l
from flask import request


class EditProfileForm(FlaskForm):
    """
    Allows a user to edit their profile.
    Ensures there are no duplicaes usernames.
    """
    username = StringField(_l('Username'), validators=[DataRequired()])
    about_me = TextAreaField(_l('About me'), validators=[Length(min=0, max=140)])
    submit = SubmitField(_l('Submit'))

    def __init__(self, original_username, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError(_l('Please use a different name.'))



# Invisible Form for following other users
class EmptyForm(FlaskForm):
    submit = SubmitField(_l('Submit'))



class PostForm(FlaskForm):
    """
    Form for creating posts.
    """
    post = TextAreaField(_l('Say something'), validators=[DataRequired(), Length(min=1, max=140)])
    submit = SubmitField(_l('Submit'))



class SearchForm(FlaskForm):
    """
    Form for searching posts.
    """
    q = StringField(_l('Search'), validators=[DataRequired()])
    
    def __init__(self, *args, **kwargs):
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        if 'csrf_enabled' not in kwargs:
            kwargs['csrf_enabled'] = False
        super(SearchForm, self).__init__(*args, **kwargs)



class MessageForm(FlaskForm):
    """
    Form for sending private messages to other users.
    """
    message = TextAreaField(_l('Message'), validators=[
        DataRequired(), Length(min=0, max=140)])
    submit = SubmitField(_l('Submit'))