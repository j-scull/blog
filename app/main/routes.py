from flask import render_template, flash, redirect, url_for, request, g, jsonify, current_app
from app import db
from app.main import bp
from app.main.forms import EditProfileForm, EmptyForm, PostForm, SearchForm, MessageForm
from flask_login import current_user, login_required
from app.models import User, Post, Message
from werkzeug.urls import url_parse
from datetime import datetime
from flask_babel import get_locale, lazy_gettext as _l
from guess_language import guess_language
from app.translate import translate



@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
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
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        g.search_form = SearchForm()
    g.locale = str(get_locale())


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
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
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    return render_template('index.html', title=_l('Explore'), posts=posts.items)


@bp.route('/translate', methods=['POST'])
@login_required
def translate_text():
    return jsonify({'text': translate(request.form['text'],
                                      request.form['source_language'],
                                      request.form['dest_language'])})


@bp.route('/search')
@login_required
def search():
    print('oooooooooooooooooooooooooo')
    if not g.search_form.validate():
        print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
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
    user = User.query.filter_by(username=username).first_or_404()
    form = EmptyForm()
    return render_template('user_popup.html', user=user, form=form)


@bp.route('/send_message/<recipient>', methods=['GET', 'POST'])
@login_required
def send_message(recipient):
    user = User.query.filter_by(username=recipient).first_or_404()
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(author=current_user, recipient=user,
                      body=form.message.data)
        db.session.add(msg)
        db.session.commit()
        flash(_l('Your message has been sent.'))
        return redirect(url_for('main.user', username=recipient))
    return render_template('send_message.html', title=_l('Send Message'),
                           form=form, recipient=recipient)


@bp.route('/messages')
@login_required
def messages():
    current_user.last_message_read_time = datetime.utcnow()
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



# for joe@joe.com
#127.0.0.1:5000.reset_password_request/eyJ0eXAiOiJKV1QiLCJhbGciOiJiUzI1NiJ9.eyJyZXNldF9wYXNzd29yZCI6MSwiZXhwIjoxNjA2MzA1NzM2LjkxOTk2NTd9.CikNPDhurpEJ2N5BaDi78lvBEs_g4vAyf4_QWOz1dMg