"""
View functions that handle authentication.
"""

from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_user, logout_user
from werkzeug.urls import url_parse
from app import db
from app.models import User
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm,  ResetPasswordRequestForm, ResetPasswordForm
from app.auth.email import send_password_reset_email
from flask_babel import lazy_gettext as _l


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles user logins.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first() 
        if user is None or not user.check_password(form.password.data):
            flash(_l('Invalid username or password'))
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')
        return redirect(next_page)
    return render_template('auth/login.html', title=_l('Sign In'), form=form)



@bp.route('/logout')
def logout():
    """
    Logs a user out of the blog.
    """
    logout_user()
    return redirect(url_for('main.index'))



@bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Registers a new user with the blog.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(_l('Registration successful'))
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title=_l('Register'), form=form)



@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    """
    Handles requests to reset passwords
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash(_l('Check your email for the instructions to reset your password'))
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html', title=_l('Reset Password'), form=form)



@bp.route('/reset_password_request/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """
    Handles password resets.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('main.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash(_l('Your password has been reset.'))
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)