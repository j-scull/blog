"""
Handles the main view function logic for the blog.
Additional view functions for authentication and error handling can be found in the auth/ and errors/ packages respectively.
"""

from flask import render_template, flash, redirect, url_for, request, g, jsonify, current_app
from app import db
from app.main import bp
from app.main.forms import EditProfileForm, EmptyForm, PostForm, SearchForm, MessageForm
from flask_login import current_user, login_required
from app.models import User, Post, Message, Notification
from werkzeug.urls import url_parse
from datetime import datetime
from flask_babel import get_locale, lazy_gettext as _l
from guess_language import guess_language
from app.translate import translate



@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    """
    Renders the index page - a user's home page, and handles the logic for writing a post.
    --------------------------------------------------------------------------------------
    Returns: the initial landing page of the blog, if a user is logged in this is there home page.
    If the user is not logged in, they are re-directed to the login page.
    """
    form = PostForm()

    if form.validate_on_submit():
        # try to identify the language being used
        language = guess_language(form.post.data)
        if language == 'UNKNOWN' or len(language) > 5:
            language = ''
        post = Post(body=form.post.data, author=current_user, language=language)
        db.session.add(post)
        db.session.commit()
        flash(_l('Your post is now live!'))
        # Post/Redirect/Get pattern
        return redirect(url_for('main.index'))

    page = request.args.get('page', 1, type=int)
    posts = current_user.followed_posts().paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    # posts.items is used to retrieve posts from the paginated object 
    return render_template('index.html', title=_l('Home'), form=form, posts=posts.items)



@bp.route('/user/<username>')
@login_required
def user(username):
    """
    Renders a user's hompage - allows for searching other users of the blog.
    ------------------------------------------------------------------------
    Parameters:
    username - the username of a user with an account on the blog.
    ------------------------------------------------------------------------
    Returns: the home page of the given user.
    If the user is not logged in, they are re-directed to the login page.
    """
    user = User.query.filter_by(username=username).first_or_404()
    # posts = [
    #     {'author': user, 'body': 'Test post #1'},
    #     {'author': user, 'body': 'Test post #2'}
    # ]
    page = request.args.get('page', 1, type=int)
    posts = user.user_posts().paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    form = EmptyForm()
    return render_template('user.html', user=user, posts=posts.items, form=form)



@bp.before_request
def before_request():
    """
    Flask before_request decorator registers a function to be called before all requests.
    Adds a last visited time for a user to their profile - this is translated to the appropriate language.
    Also renders the search box for searching posts.
    """
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        g.search_form = SearchForm()
    g.locale = str(get_locale())



@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """
    Renders a page that allows a user to edit their profile.
    --------------------------------------------------------
    Returns: a form that allows a user to edit their profile.
    If the user is not logged in, they are re-directed to the login page.
    """
    form = EditProfileForm(current_user.username)
    
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash(_l('Your changes have been saved'))
        return redirect(url_for('main.edit_profile'))
    
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    
    return render_template('edit_profile.html', title=_l('Edit Profile'), form=form)



@bp.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    """
    Handles the logic for following another user.
    ---------------------------------------------
    Parameter:
    username - the user to unfollow
    ---------------------------------------------
    Returns: The followed user's home page if successful, or the current user's home page if unsuccessful.
    If the user is not logged in, they are re-directed to the login page.
    """
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        
        if user is None:
            flash(_l('User %(username)s not found'))
            #flash('User {} not found'.format(username))
            return redirect(url_for('main.index'))
        
        if user == current_user:
            flash(_l('You cannot follow yourself!'))
            return redirect(url_for('main.user', username=username))
        
        current_user.follow(user)
        db.session.commit()
        flash(_l('You are following %(username)s'))
        #flash('You are following {}!'.format(username))
        return redirect(url_for('main.user', username=username))
    
    else:
        return redirect(url_for('main.index'))



@bp.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    """
    Handles the logic for unfollowing another user.
    -----------------------------------------------
    Parameter:
    username - the user to unfollow
    -----------------------------------------------
    Returns: The unfollowed user's home page if successful, or the current user's home page if unsuccessful.
    If the user is not logged in, they are re-directed to the login page.
    """
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        
        if user is None:
            flash(_l('User %(username)s not found'))
            #flash('User {} not found.'.format(username))
            return redirect(url_for('main.index'))
        
        if user == current_user:
            flash('You cannot unfollow yourself!')
            return redirect(url_for('main.user', username=username))
        
        current_user.unfollow(user)
        db.session.commit()
        flash(_l('You are no longer following %(username)s'))
        #flash('You are no longer following {}.'.format(username))
        return redirect(url_for('main.user', username=username))
    
    else:
        return redirect(url_for('main.index'))



# view all posts
@bp.route('/explore')
@login_required
def explore():
    """
    Renders all post made by all users on the blog
    ----------------------------------------------
    Returns: a paginated list of posts by users
    If the user is not logged in, they are re-directed to the login page.
    """
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    return render_template('index.html', title=_l('Explore'), posts=posts.items)



@bp.route('/translate', methods=['POST'])
@login_required
def translate_text():
    """
    Translates text written in a foreign language to the language of the current user.
    Requires the Azure Translater API service to be set up.
    """
    return jsonify({'text': translate(request.form['text'],
                                      request.form['source_language'],
                                      request.form['dest_language'])})



@bp.route('/search')
@login_required
def search():
    """
    Implements a search functionality fo posts (Elastic Search needs to be enabled)
    -------------------------------------------------------------------------------
    Returns: a paginated list of relevant search results, or does nothing if Elastic search is not enabled.
    If the user is not logged in, they are re-directed to the login page.
    """
    if not g.search_form.validate():
        return redirect(url_for('main.explore'))
    
    page = request.args.get('page', 1, type=int)
    posts, total = Post.search(g.search_form.q.data, page, 
                            current_app.config['POSTS_PER_PAGE'])
    
    next_url = url_for('main.search', q=g.search_form.q.data, page=page + 1) \
        if total > page * current_app.config['POSTS_PER_PAGE'] else None
    
    prev_url = url_for('main.search', q=g.search_form.q.data, page=page - 1) \
        if page > 1 else None
    
    return render_template('search.html', title=_l('Search'), posts=posts,
                            next_url=next_url, prev_url=prev_url)



@bp.route('/user/<username>/popup')
@login_required
def user_popup(username):
    """
    Creates a small popup of user profile details if mouseover a user's name or avatar.
    -----------------------------------------------------------------------------------
    Parameters:
    username - the user being looked at.
    -----------------------------------------------------------------------------------
    Returns: a popup displaying user details. 
    If the user is not logged in, they are re-directed to the login page.
    """
    user = User.query.filter_by(username=username).first_or_404()
    form = EmptyForm()
    return render_template('user_popup.html', user=user, form=form)



@bp.route('/send_message/<recipient>', methods=['GET', 'POST'])
@login_required
def send_message(recipient):
    """
    Handles the logic for users to send private messages to each other.
    -------------------------------------------------------------------
    Parameters:
    recipient - the user the message is being sent to.
    -------------------------------------------------------------------
    Returns: the recipients home page
    If the user is not logged in, they are re-directed to the login page.
    """
    user = User.query.filter_by(username=recipient).first_or_404()
    form = MessageForm()
    
    if form.validate_on_submit():
        msg = Message(author=current_user, recipient=user,
                      body=form.message.data)
        db.session.add(msg)
        user.add_notification('unread_message_count', user.new_messages())
        db.session.commit()
        flash(_l('Your message has been sent.'))
        return redirect(url_for('main.user', username=recipient))
    
    return render_template('send_message.html', title=_l('Send Message'),
                           form=form, recipient=recipient)



@bp.route('/messages')
@login_required
def messages():
    """
    Displays all messages for a user.
    ---------------------------------
    Returns: a pagenated list messages.
    If the user is not logged in, they are re-directed to the login page.
    """
    current_user.last_message_read_time = datetime.utcnow()
    current_user.add_notification('unread_message_count', 0)
    db.session.commit()
    page = request.args.get('page', 1, type=int)
    
    messages = current_user.messages_received.order_by(
        Message.timestamp.desc()).paginate(
            page, current_app.config['POSTS_PER_PAGE'], False)
    
    next_url = url_for('main.messages', page=messages.next_num) \
        if messages.has_next else None
    
    prev_url = url_for('main.messages', page=messages.prev_num) \
        if messages.has_prev else None
    
    return render_template('messages.html', messages=messages.items,
                            next_url=next_url, prev_url=prev_url)



@bp.route('/notifications')
@login_required
def notifications():
    """
    Handles the client polling for message notificaions (these happen every 10 seconds).
    ------------------------------------------------------------------------------------
    If the user is not logged in, they are re-directed to the login page.
    """
    since = request.args.get('since', 0.0, type=float)
    notifications = current_user.notifications.filter(
        Notification.timestamp > since).order_by(Notification.timestamp.asc())
    return jsonify([{
        'name': n.name,
        'data': n.get_data(),
        'timestamp': n.timestamp
    } for n in notifications])