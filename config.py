

# config.py
import re
from functools import wraps
from urllib import request
import os

import pyotp
from flask import Flask, url_for, render_template, flash, redirect, request
from flask_login import LoginManager, UserMixin, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import MetaData
from datetime import timedelta, datetime
from werkzeug.security import generate_password_hash, check_password_hash

from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_admin.menu import MenuLink
import logging
import base64
import secrets
from dotenv import load_dotenv
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

app = Flask(__name__)

login_manager = LoginManager()

# DATABASE CONFIGURATION
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config['SQLALCHEMY_ECHO'] = bool(os.getenv("SQLALCHEMY_ECHO"))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = bool(os.getenv("SQLALCHEMY_TRACK_MODIFICATIONS"))
app.config['RECAPTCHA_USE_SSL'] = bool(os.getenv("RECAPTCHA_USE_SSL"))
app.config["RECAPTCHA_PUBLIC_KEY"] = os.getenv("RECAPTCHA_PUBLIC_KEY")
app.config["RECAPTCHA_PRIVATE_KEY"] = os.getenv("RECAPTCHA_PRIVATE_KEY")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=(int(os.getenv("PERMANENT_SESSION_LIFETIME"))))
app.config['FLASK_ADMIN_FLUID_LAYOUT'] = bool(os.getenv("FLASK_ADMIN_FLUID_LAYOUT"))
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")

metadata = MetaData(
    naming_convention={
        "ix": 'ix_%(column_0_label)s',
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    }
)

db = SQLAlchemy(app, metadata=metadata)
migrate = Migrate(app, db)

# login manger setup
login_manager.init_app(app)
login_manager.login_view = "views.login_page"
login_manager.login_message = "You need to log in to access this page."
login_manager.login_message_category = "danger"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["50 per day", "30 per 2 hour"],
    app=app
)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.errorhandler(400)
def bad_request(error):
    return render_template("errors/400.html"), 400


@app.errorhandler(404)
def not_found(error):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def internal_serve_error(error):
    return render_template("errors/500.html"), 500


@app.errorhandler(501)
def not_implemented(error):
    return render_template("errors/501.html"), 501


@app.errorhandler(429)
def limitation_error(error):
    return render_template("errors/429.html"), 429


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created = db.Column(db.DateTime, nullable=False)
    title = db.Column(db.Text, nullable=False)
    body = db.Column(db.Text, nullable=False)
    user = db.relationship("User", back_populates="posts")

    def __init__(self, user_id, title, body):
        self.created = datetime.now()
        self.user_id = user_id
        self.title = title
        self.body = body

    def update(self, title, body):
        self.created = datetime.now()
        self.title = title
        self.body = body
        db.session.commit()


class Log(db.Model):
    __tablename__ = 'logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    registration = db.Column(db.DateTime, nullable=False)
    latest_login = db.Column(db.DateTime, nullable=True)
    previous_login = db.Column(db.DateTime, nullable=True)
    latest_ip = db.Column(db.String(12), nullable=True)
    previous_ip = db.Column(db.String(12), nullable=True)
    user = db.relationship("User", back_populates="log")

    def __init__(self, user_id):
        self.user_id = user_id
        self.registration = datetime.now()


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    # User authentication information.
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(256))
    # User information
    firstname = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(100), nullable=False)
    # User posts
    posts = db.relationship("Post", back_populates="user")
    mfa_key = db.Column(db.String(100), nullable=False, default=pyotp.random_base32())
    mfa_enable = db.Column(db.Boolean, nullable=False, default=False)
    role = db.Column(db.String(100), nullable=False, default='end_user')
    log = db.relationship("Log", uselist=False, back_populates="user")
    salt = db.Column(db.String(100), nullable=False)

    def __init__(self, email, firstname, lastname, phone, password):
        self.email = email
        self.firstname = firstname
        self.lastname = lastname
        self.phone = phone
        self.password_hash = generate_password_hash(password)
        self.mfa_key = pyotp.random_base32()
        self.mfa_enable = False
        self.role = 'end_user'
        self.salt = base64.b64encode(secrets.token_bytes(32)).decode()

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_log(self):
        log = Log(user_id=self.id)
        log.latest_ip = request.remote_addr
        log.latest_login = log.registration
        db.session.add(log)
        db.session.commit()


# DATABASE ADMINISTRATOR
class MainIndexLink(MenuLink):
    def get_url(self):
        return url_for('index', _external=True, _scheme='https')


class PostView(ModelView):
    column_display_pk = True
    column_hide_backrefs = False
    column_list = ('id', 'user_id', 'created', 'title', 'body', 'user')
    can_create = False
    can_edit = False
    can_delete = False

    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == "db_admin"

    def inaccessible_callback(self, name, **kwargs):
        if current_user.is_authenticated:
            return redirect(url_for("accounts.forbidden"))
        flash("Access to DB Admin is not allowed")
        return redirect(url_for("accounts.login"))


class UserView(ModelView):
    column_display_pk = True  # optional, but I like to see the IDs in the list
    column_hide_backrefs = False
    column_list = (
        'id', 'email', 'password_hash', 'firstname', 'lastname', 'phone', 'role', 'posts', 'mfa_key', 'mfa_enable')
    can_create = False
    can_edit = False
    can_delete = False

    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == "db_admin"

    def inaccessible_callback(self, name, **kwargs):
        if current_user.is_authenticated:
            return redirect(url_for("accounts.forbidden"))
        flash("Access to DB Admin is not allowed")
        return redirect(url_for("accounts.login"))


admin = Admin(app, name='DB Admin', template_mode='bootstrap4')
admin._menu = admin._menu[1:]
admin.add_link(MainIndexLink(name='Home Page'))
admin.add_view(PostView(Post, db.session))
admin.add_view(UserView(User, db.session))


def roles_required(*roles):
    def inner_decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                return redirect(url_for("accounts.forbidden"))
            return f(*args, **kwargs)

        return wrapped

    return inner_decorator


# set logger
logger = logging.getLogger("__LoggerForFile__")
handler = logging.FileHandler('logs.log', mode="a")
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# import blueprints
from accounts.api import api_accounts
from accounts.views import views
from posts.views import posts_bp
from security.views import security_bp

# register blueprints with app
app.register_blueprint(api_accounts)
app.register_blueprint(views)
app.register_blueprint(posts_bp)
app.register_blueprint(security_bp)

# using waf policy
conditions = {
    "SQL injection": re.compile("(Union|Select|Insert|Drop|Alter|;|')", re.IGNORECASE),
    "XXS": re.compile(" <script>|<iframe>|%3Cscript%3E|%3Ciframe%3E", re.IGNORECASE),
    "Path traversal": re.compile(r"(\.\./|\.\.|%2e%2e%2f|%2e%2e/|\.\.%2f)", re.IGNORECASE)
}


@app.before_request
def waf_function():
    for attack_type, attack_pattern in conditions.items():
        if attack_pattern.search(request.path) or attack_pattern.search(request.query_string.decode()):
            logger.warning(f"Dangerous operation: {attack_type} attack found, user enter: {request.path}")

            return render_template("errors/waf_error.html", label=attack_type)


csp = {
    'script-src': [
        'https://www.google.com/recaptcha/',
        'https://www.gstatic.com/recaptcha/',
        'https://cdn.jsdelivr.net',
        "'unsafe-inline'"
    ],
    'frame-src': [

        'https://www.google.com/recaptcha/',
        'https://recaptcha.google.com/recaptcha/'
    ],
    'style-src': [

        'https://cdn.jsdelivr.net',
        "'unsafe-inline'"
    ]
}

tailsman = Talisman(app, content_security_policy=csp)


