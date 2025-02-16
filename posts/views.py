from flask import Blueprint, render_template, flash, url_for, redirect, request, session
from config import Post, db, User
from posts.forms import PostForm
from sqlalchemy import desc
from flask_login import current_user
from flask_login import login_required
from config import roles_required, logger
from cryptography.fernet import Fernet
from hashlib import scrypt
import base64

posts_bp = Blueprint('posts', __name__, template_folder='templates')


@posts_bp.route('/posts')
@login_required
@roles_required("end_user")
def view():
    all_posts = Post.query.order_by(desc("id")).all()
    for post in all_posts:
        creator = User.query.filter_by(id=post.user_id).first()  # find specific user who creat his own post
        cipher = generate_kdf_key(creator)  # generate creator his own specific cipher key
        post.title = cipher.decrypt(post.title.encode()).decode()
        post.body = cipher.decrypt(post.body.encode()).decode()

    return render_template('posts/posts.html', posts=all_posts)


@posts_bp.route('/create', methods=['GET', 'POST'])
@login_required
@roles_required("end_user")
def create():
    cipher = generate_kdf_key(current_user)  # user have its unique cipher to encrypt post
    form = PostForm()

    if form.validate_on_submit():
        encrypt_title = cipher.encrypt(form.title.data.encode()).decode()
        encrypt_body = cipher.encrypt(form.body.data.encode()).decode()
        new_post = Post(user_id=current_user.get_id(), title=encrypt_title, body=encrypt_body)
        db.session.add(new_post)
        db.session.commit()

        logger.warning(f"User email: {current_user.email}, User role: {current_user.role}, Post ID: {new_post.id}, "
                       f"User IP: {current_user.log.latest_ip} Post Creation")
        flash('Post created', category='success')
        return redirect(url_for('posts.view'))

    return render_template('posts/create.html', form=form)


@posts_bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
@roles_required("end_user")
def update(id):
    cipher = generate_kdf_key(current_user)
    post_to_update = Post.query.filter_by(id=id).first()

    if not post_to_update:
        return redirect(url_for('posts.view'))

    if post_to_update.user != current_user:
        flash('You are not authorized to update this post', category='danger')
        return redirect(url_for('posts.view'))

    title_decrypt = cipher.decrypt(post_to_update.title.encode()).decode()
    body_decrypt = cipher.decrypt(post_to_update.body.encode()).decode()

    form = PostForm()

    if form.validate_on_submit():
        # encrypt user Input Field before Commit to Database
        encrypt_title = cipher.encrypt(form.title.data.encode()).decode()
        encrypt_body = cipher.encrypt(form.body.data.encode()).decode()
        post_to_update.update(title=encrypt_title, body=encrypt_body)

        logger.warning(
            f"User email: {current_user.email}, User role: {current_user.role}, Post ID: {post_to_update.id}, "
            f"Post author's email: {post_to_update.user.email} User IP: {current_user.log.latest_ip} Post Update")
        flash('Post updated', category='success')

        return redirect(url_for('posts.view'))

    # display previous title and body when modified
    form.title.data = title_decrypt
    form.body.data = body_decrypt

    return render_template('posts/update.html', form=form)


@posts_bp.route('/<int:id>/delete')
@login_required
@roles_required("end_user")
def delete(id):
    delete_post = Post.query.filter_by(id=id).first()
    if delete_post.user != current_user:
        flash('You are not authorized to delete this post', category='danger')
        return redirect(url_for('posts.view'))
    else:
        db.session.delete(delete_post)
        db.session.commit()

    logger.warning(f"User email: {current_user.email}, User role: {current_user.role}, Post ID: {delete_post.id}, "
                   f"Post author's email: {delete_post.user.email} User IP: {current_user.log.latest_ip}, Post Delete")

    flash('Post deleted', category='success')
    return redirect(url_for('posts.view'))


def generate_kdf_key(user):
    get_user_password = session.get("user_password")
    user_salt = user.salt
    # generate specific key for each user based on their password and salt, using kdf
    key = scrypt(
        password=get_user_password.encode(),
        salt=user_salt.encode(),
        n=2048,
        r=8,
        p=1,
        dklen=32)
    user_private_key = base64.b64encode(key)
    cipher = Fernet(user_private_key)

    return cipher
