from datetime import datetime
from flask import request
import qrcode
from flask import Blueprint, render_template, flash, redirect, url_for, session
from markupsafe import Markup
import pyotp
from accounts.forms import RegistrationForm, LoginForm
from config import User, db, Post, roles_required, limiter
from flask_login import login_user, current_user, login_required, logout_user
from config import logger
from posts.views import generate_kdf_key

# accounts_bp = Blueprint('accounts', __name__, template_folder='templates')
#
#
# @accounts_bp.route('/registration', methods=['GET', 'POST'])
# @limiter.limit("500 per day", error_message="You have too many register requests")
# def registration():
#     form = RegistrationForm()
#
#     if form.validate_on_submit():
#         user = User.query.filter_by(email=form.email.data).first()
#
#         if user is not None:
#             flash("Email already exists", category="danger")
#             return render_template("accounts/registration.html", form=form)
#
#         new_user = User(email=form.email.data,
#                         firstname=form.firstname.data,
#                         lastname=form.lastname.data,
#                         phone=form.phone.data,
#                         password=form.password.data,
#                         )
#
#         db.session.add(new_user)
#         db.session.commit()
#
#         new_user.generate_log()
#         login_user(new_user)
#         logger.warning(f"User:{new_user.email}, Role:{new_user.role}, IP:{new_user.log.latest_ip} User registration")
#
#         flash("Account created. You must enable Multi-Factor Authentication first to login", category="success")
#         return redirect(url_for("accounts.setup_mfa"))
#
#     return render_template("accounts/registration.html", form=form)
#
#
# @accounts_bp.route('/login', methods=['GET', 'POST'])
# @limiter.limit("2000 per hour", error_message="You have too many login requests")
# def login():
#     # set session to trace login attempts
#     if not session.get("attempted_login"):
#         session["attempted_login"] = 0
#
#     form = LoginForm()
#
#     if form.validate_on_submit():
#         user = User.query.filter_by(email=form.email.data).first()
#         # check use existence and password
#         if user is not None and user.check_password(form.password.data):
#             # fetch user password when enter in login form and used in kdf function
#             user_password = form.password.data
#             session["user_password"] = user_password  # store password
#
#             mfa_auth = pyotp.TOTP(user.mfa_key).verify(form.mfa_code.data)
#             # If MFA not enabled for the current user
#             if not user.mfa_enable:
#                 if mfa_auth:
#                     # enable mfa and commited when first login with mfa is correct
#                     user.mfa_enable = True
#                     login_user(user)
#                     # set login attempt to 0 if successful login
#                     session["attempted_login"] = 0
#                     log_handle(user)  # record time and ip info
#                     # record more detail, email, role, ip for current login user
#                     logger.warning(f"User:{user.email}, Role:{user.role}, IP:{user.log.latest_ip} User login")
#                     session.permanent = True
#
#                     flash("MFA detected and correct, login successfully", category="success")
#
#                     # redirect user based on their role
#                     if user.role == "end_user":
#                         return redirect(url_for("posts.view"))
#                     elif user.role == "db_admin":
#                         return redirect(url_for("admin.index", _scheme="https", _external=True))
#                     elif user.role == "sec_admin":
#                         return redirect(url_for("accounts.security"))
#
#             # if mfa still not enable
#             if not user.mfa_enable:
#                 flash("You have not enable Multi-Factor Authentication. Please enable first to login.",
#                       category="danger")
#                 session["attempted_login"] += 1
#                 logger.warning(
#                     f"User email: {user.email}, Attempts:{session.get("attempted_login")}, IP:{user.log.latest_ip} Invalid login attempt")
#
#                 return redirect(url_for('accounts.setup_mfa'))
#             # when mfa already enabled
#             else:
#                 return handle_mfa_enable_login(user, form)
#
#         # handle none user or wrongful password
#         else:
#             session["attempted_login"] += 1
#             remaining_time = 3 - session.get("attempted_login")
#
#             if remaining_time > 0 and remaining_time != 3:
#                 flash(f"Password invalid or user account do not exist, {remaining_time} login attempts remaining.",
#                       "danger")
#                 return render_template("accounts/login.html", form=form, lock=False)
#             else:
#                 # log user ip and its email who reached max retries, and lock its account
#                 logger.warning(
#                     f"User: {user.email}, Attempts: {session.get("attempted_login")}, IP: {user.log.latest_ip} Maximum invalid login attempts reached")
#                 account_lock()
#                 return render_template("accounts/login.html", lock=True)
#
#     return render_template('accounts/login.html', form=form, lock=False)
#
#
# def handle_mfa_enable_login(user, form):
#     mfa_auth = pyotp.TOTP(user.mfa_key).verify(form.mfa_code.data)
#     # if mfa code is correct, log user in, and reset attempt counter
#     if mfa_auth:
#         session["attempted_login"] = 0
#         session.permanent = True
#         login_user(user)
#         log_handle(user)
#         logger.warning(f"User:{user.email}, Role:{user.role}, IP:{user.log.latest_ip} User login")
#
#         flash("MFA detected and correct, login successfully", category="success")
#
#         # redirect user based on their role
#         if user.role == "end_user":
#             return redirect(url_for("posts.view"))
#         elif user.role == "db_admin":
#             return redirect(url_for("admin.index"))
#         elif user.role == "sec_admin":
#             return redirect(url_for("accounts.security"))
#
#     # mfa code is incorrect
#     else:
#         session["attempted_login"] += 1
#         remaining_time = 3 - session.get("attempted_login")
#
#         # if still have valid remaining time, log user info
#         if remaining_time > 0 and remaining_time != 3:
#             logger.warning(
#                 f"User email: {user.email}, Attempts:{session.get("attempted_login")}, IP:{user.log.latest_ip} Invalid login attempt")
#             flash(f"MFA code incorrect, {remaining_time} login attempts remaining.", "danger")
#             return render_template("accounts/login.html", form=form, lock=False)
#         # remaining time is out of usage, lock account and log more detail
#         else:
#             logger.warning(
#                 f"User: {user.email}, Attempts: {session.get("attempted_login")}, IP: {user.log.latest_ip} Maximum invalid login attempts reached")
#             account_lock()
#             return render_template("accounts/login.html", lock=True)
#
#
# # display a useful message and a button to unlink account
# def account_lock():
#     flash(Markup(
#         'No login chance left, too many time fails, please unlock your account at <div class="text-center"><a href="/unlock" '
#         'class="btn btn-primary" '
#         'role="button" style="margin-top: 10px">Unlock-Account</a></div>')
#         , "danger")
#
#
# # log user ip and login time info
# def log_handle(user):
#     user.log.previous_login = user.log.latest_login
#     user.log.previous_ip = user.log.latest_ip
#
#     user.log.latest_login = datetime.now()
#     user.log.latest_ip = request.remote_addr
#
#     db.session.commit()
#
#
# @accounts_bp.route('/logout')
# @login_required
# def logout():
#     logout_user()
#     return redirect(url_for("accounts.login"))
#
#
# @accounts_bp.route('/account')
# @login_required
# @roles_required('end_user', 'sec_admin', 'db_admin')
# def account():
#     user = current_user
#     # only show posts created by its currently login account
#     cipher = generate_kdf_key(user)
#     encrypted_posts = Post.query.filter_by(user_id=user.id).all()
#
#     for post in encrypted_posts:
#         post.title = cipher.decrypt(post.title.encode()).decode()
#         post.body = cipher.decrypt(post.body.encode()).decode()
#
#     return render_template('accounts/account.html', use_info=user, posts=encrypted_posts)
#
#
# @accounts_bp.route('/unlock', methods=['GET', 'POST'])
# @login_required
# @roles_required('db_admin')
# def unlock():
#     session['attempted_login'] = 0
#     return redirect(url_for('accounts.login'))
#
#
# @accounts_bp.route('/setup_mfa', methods=['GET', 'POST'])
# @login_required
# def setup_mfa():
#     mfa_key = current_user.mfa_key
#     uri = pyotp.TOTP(mfa_key).provisioning_uri(current_user.email, issuer_name="Blog")
#
#     file_name = f"{current_user.firstname}_qrcode.png"
#     qrcode.make(uri).save(f"static/{file_name}")
#
#     return render_template('accounts/setup_mfa.html', mfa_key=mfa_key, code_img=file_name)
#
#
# @accounts_bp.route('/security', methods=['GET', 'POST'])
# @login_required
# @roles_required("sec_admin")
# def security():
#     users = User.query.all()
#     filePath = "logs.log"
#     with open(filePath, "r") as f:
#         log = f.readlines()[-10]
#
#     return render_template("security/security.html", user=users, logs=log)
#
#
# @accounts_bp.route("/forbidden")
# @login_required
# def forbidden():
#     return render_template("errors/forbidden.html")

# accounts/views.py
from flask import Blueprint, render_template
from accounts.forms import RegistrationForm, LoginForm

views = Blueprint('views', __name__)

@views.route('/login')
def login_page():
    form = LoginForm()
    return render_template('accounts/login.html', form=form)

@views.route('/registration', methods=['GET'])
def registration_page():
    form = RegistrationForm()
    return render_template('accounts/registration.html', form=form)

@views.route('/setup_mfa')
def setup_mfa_page():
    return render_template('accounts/setup_mfa.html')

@views.route('/account')
def account_page():
    return render_template('accounts/account.html')

