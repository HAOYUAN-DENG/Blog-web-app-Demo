# accounts/api.py
from flask import Blueprint, request, jsonify
from config import User, db, logger, Post, roles_required
import pyotp
from flask_login import login_user, logout_user, current_user, login_required
from datetime import datetime
import qrcode
import io
import base64
import secrets
from flask import session  # Import session from Flask

from posts.views import generate_kdf_key

# Create a blueprint for the RESTful accounts API
api_accounts = Blueprint('api_accounts', __name__, url_prefix='/api/accounts')

@api_accounts.route('/register', methods=['POST'])
def api_register():
    """
    RESTful endpoint for user registration.
    Expects a JSON payload with:
      - email
      - firstname
      - lastname
      - phone
      - password
      - confirm_password
    Returns a JSON response with a message and HTTP status code.
    """
    data = request.get_json()
    if not data:
        return jsonify(message="Missing JSON body."), 400

    email = data.get("email")
    firstname = data.get("firstname")
    lastname = data.get("lastname")
    phone = data.get("phone")
    password = data.get("password")
    confirm_password = data.get("confirm_password")

    # Check required fields
    if not all([email, firstname, lastname, phone, password, confirm_password]):
        return jsonify(message="All fields are required."), 400

    # Ensure the password and confirm password match
    if password != confirm_password:
        return jsonify(message="Passwords do not match."), 400

    # Check if a user with this email already exists
    if User.query.filter_by(email=email).first() is not None:
        return jsonify(message="Email already exists."), 409

    # Create a new user. Note that User.__init__ automatically hashes the password,
    # creates a MFA key, and sets a default role.
    new_user = User(email=email,
                    firstname=firstname,
                    lastname=lastname,
                    phone=phone,
                    password=password)
    db.session.add(new_user)
    db.session.commit()

    # Generate an initial log for the new user.
    new_user.generate_log()

    # Log the user in
    login_user(new_user)
    logger.warning(f"User registered: {new_user.email}, Role: {new_user.role}, IP: {new_user.log.latest_ip}")

    return jsonify(message="User registered successfully."), 201

@api_accounts.route('/login', methods=['POST'])
def api_login():
    """
    RESTful endpoint for user login.
    Expects a JSON payload with:
      - email
      - password
      - mfa_code (optional, but required if MFA is enabled or for first-time MFA setup)

    The logic is as follows:
      1. If the user does not exist or the password is incorrect, return an error.
      2. If the user has not enabled MFA:
         - If a valid MFA code is provided, enable MFA and log the user in.
         - Otherwise, return an error prompting the client to set up MFA.
      3. If MFA is already enabled, verify the provided MFA code and log the user in.
    """
    data = request.get_json()
    if not data:
        return jsonify(message="Missing JSON body."), 400

    # Initialize login attempts counter if not present
    if "attempted_login" not in session:
        session["attempted_login"] = 0

    email = data.get("email")
    password = data.get("password")
    mfa_code = data.get("mfa_code", "")

    if not email or not password:
        return jsonify(message="Email and password are required."), 400

    user = User.query.filter_by(email=email).first()
    # Check if user exists and password is correct
    if user is None or not user.check_password(password):
        session["attempted_login"] += 1
        remaining = 3 - session["attempted_login"]
        if remaining > 0:
            return jsonify(message=f"Invalid email or password. {remaining} attempts remaining."), 401
        else:
            return jsonify(message="Maximum login attempts reached, please unlock your account."), 429

    # Reset the counter on a valid password
    session["attempted_login"] = 0

    # If MFA has not been enabled for this user yet, check the provided mfa_code
    if not user.mfa_enable:
        if mfa_code and pyotp.TOTP(user.mfa_key).verify(mfa_code):
            # Enable MFA on the first successful verification
            user.mfa_enable = True
            db.session.commit()
            session["user_password"] = password  # the plain text password from the login form
            login_user(user)
            logger.warning(f"User login (MFA setup): {user.email}, IP: {user.log.latest_ip}")
            return jsonify(message="Login successful and MFA enabled."), 200
        else:
            # Inform the client that MFA is required for login
            return jsonify(message="MFA not enabled. Please call /setup_mfa to get your MFA configuration."), 403
    else:
        # For users with MFA enabled, verify the provided MFA code
        if not pyotp.TOTP(user.mfa_key).verify(mfa_code):
            session["attempted_login"] += 1
            remaining = 3 - session["attempted_login"]
            if remaining > 0:
                return jsonify(message=f"Invalid MFA code. {remaining} attempts remaining."), 403
            else:
                return jsonify(message="Maximum login attempts reached, please unlock your account."), 429

        else:
            session["user_password"] = password  # the plain text password from the login form
            login_user(user)
            # Update user log information on login
            user.log.previous_login = user.log.latest_login
            user.log.previous_ip = user.log.latest_ip
            user.log.latest_login = datetime.now()
            user.log.latest_ip = request.remote_addr

            db.session.commit()
            logger.warning(f"User login: {user.email}, IP: {user.log.latest_ip}")
            return jsonify(message="Login successful."), 200

@api_accounts.route('/logout', methods=['POST'])
@login_required
def api_logout():
    """
    RESTful endpoint for logging out the current user.
    Returns a JSON message indicating success.
    """
    logout_user()
    return jsonify(message="Logged out successfully."), 200

@api_accounts.route('/account', methods=['GET'])
@login_required
def api_account():
    """
    RESTful endpoint to get the account details for the current user.
    Returns a JSON object containing user info and the user's posts.
    """
    user = current_user
    # Create the cipher for the current user using their password stored in session
    cipher = generate_kdf_key(current_user)
    # Query user posts (assuming posts are stored in the Post table with a foreign key to user)
    posts = Post.query.filter_by(user_id=current_user.get_id()).all()

    # Prepare a list to hold decrypted posts data
    decrypted_posts = []

    for post in user.posts:
        # Decrypt title and body using the cipher
        decrypted_title = cipher.decrypt(post.title.encode()).decode()
        decrypted_body = cipher.decrypt(post.body.encode()).decode()

        decrypted_posts.append({
            'title': decrypted_title,
            'body': decrypted_body,
            'created': post.created  # Assuming post.created is a string or serializable format
        })

    user_info = {
        "id": user.id,
        "email": user.email,
        "firstname": user.firstname,
        "lastname": user.lastname,
        "phone": user.phone,
        "role": user.role,
        "posts": decrypted_posts
    }
    return jsonify(user_info), 200

@api_accounts.route('/setup_mfa', methods=['GET'])
def api_setup_mfa():
    """
    RESTful endpoint to retrieve the MFA setup information for the current user.
    Returns the MFA key and a QR code image encoded in base64.
    The client can use the QR code to set up MFA in an authenticator app.
    """
    mfa_key = current_user.mfa_key
    # Create a provisioning URI for MFA
    uri = pyotp.TOTP(mfa_key).provisioning_uri(current_user.email, issuer_name="Blog Demo")

    # Generate a QR code image for the provisioning URI
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert the PIL image to a base64 string
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    qr_code_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return jsonify(mfa_key=mfa_key, qr_code=qr_code_base64), 200

@api_accounts.route('/unlock', methods=['POST'])
@login_required
@roles_required('db_admin')
def api_unlock():
    """
    RESTful endpoint to unlock an account by resetting login attempts.
    Only accessible to users with the 'db_admin' role.
    Returns a JSON message indicating the account has been unlocked.
    """
    # In this RESTful design, we simply reset the attempted login counter stored in the session.
    # Note: In a real-world API, you might manage login attempts differently (e.g., in the database).
    if "attempted_login" in session:
        session["attempted_login"] = 0
    return jsonify(message="Account unlocked successfully."), 200
