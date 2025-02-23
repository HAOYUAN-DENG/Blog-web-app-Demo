# Blog Demo Application

A Flask-based blog demo project with user registration, multi-factor authentication, encrypted post creation, and role-based access control. The application demonstrates a complete web application stack with RESTful API endpoints, form validation, secure logging, and various user interfaces for registration, login, posting, and security monitoring.

---

## English

### Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [Docker](#docker)
- [Security](#security)
- [Logging](#logging)
- [API Endpoints](#api-endpoints)
- [Contributing](#contributing)
- [License](#license)

### Overview
#### quick login account/password: Q@outlook.com/991208qqW!

This project is a blog demo application built using Flask. It offers:

- User registration and login with multi-factor authentication (MFA)
- Role-based access control for end users, security administrators, and database administrators
- Post creation, viewing, updating, and deletion with encryption based on user-specific keys
- RESTful API endpoints for account management and post handling
- Detailed logging of user activities (registration, login, post operations)

### Features

- **User Authentication:** Secure registration and login with password hashing, MFA setup, and session management.
- **Multi-Factor Authentication:** MFA integration using TOTP, including QR code generation for authenticator apps.
- **Post Management:** Users can create, update, view, and delete posts. Post content is encrypted using a unique key generated from the user's password and salt.
- **Role-Based Access Control:** Different roles such as `end_user`, `sec_admin`, and `db_admin` ensure proper access to functionalities.
- **RESTful API:** API endpoints for registration, login, logout, account details, MFA setup, and account unlocking.
- **Logging and Security:** All critical actions are logged. The application also includes a basic web application firewall (WAF) to mitigate SQL injection, XSS, and path traversal attacks.

### Project Structure

```
├── app.py               # Main application entry point
├── config.py            # Configuration and application setup (database, logging, security, etc.)
├── templates/
│   ├── base.html        # Base template with navigation and common layout
│   ├── index.html       # Home page
│   ├── account.html     # User account page
│   ├── login.html       # Login page
│   ├── registration.html# Registration page
│   ├── setup_mfa.html   # MFA setup page
│   ├── posts/           # Post related templates:
│   │   ├── create.html  # Create post page
│   │   ├── update.html  # Update post page
│   │   └── posts.html   # List posts page
│   └── security.html    # Security monitoring page
├── accounts/            # Contains API and view routes for user account management
│   ├── api.py           # RESTful API endpoints for account operations
│   └── views.py         # Account-related view routes (login, registration, account, MFA)
├── posts/               # Contains post views and forms
│   └── views.py         # Post creation, update, deletion, and display logic
├── forms.py             # WTForms definitions for registration, login, and posts
└── logs.log             # Log file storing user activity logs
└── Dockerfile           # Docker setup
```

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yourusername/blog-demo.git
   cd blog-demo
   ```

2. **Set up a virtual environment and install dependencies:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**

   Create a `.env` file in the project root with the necessary configurations, for example (or use the provided .env file):

   ```env
   SQLALCHEMY_DATABASE_URI=sqlite:///blog.db
   SQLALCHEMY_ECHO=False
   SQLALCHEMY_TRACK_MODIFICATIONS=False
   PERMANENT_SESSION_LIFETIME=1
   SECRET_KEY=your_secret_key_here
   FLASK_ADMIN_FLUID_LAYOUT=True
   ```

4. **Initialize the Database:**
(or simply use the database provided called blog.db) 
   ```bash
   flask db init
   flask db migrate
   flask db upgrade
   ```

### Usage

1. **Run the Application:**

   ```bash
   flask run
   ```
   (or simply click Pycharm run UI)

2. **Access the Application:**

   Open your browser and navigate to [http://127.0.0.1:5000](http://127.0.0.1:5000).

3. **Features Overview:**

   - **Home Page:** Displays a simple welcome message.
   - **Registration & Login:** Use the registration and login pages to create an account. MFA setup is required on the first login.
   - **Post Management:** After logging in, end users can create, view, update, and delete posts.
   - **Security Page:** Accessible by security administrators to view recent security logs and user event logs.
   - **API Endpoints:** RESTful API routes are available under `/api/accounts` for operations like registration, login, account details, MFA setup, and account unlocking (accessible by `db_admin`).

### Docker

You can also run the application inside a Docker container. Follow these steps:

1. **Build the Docker Image:**

   ```bash
   docker build -t blog-demo .
   ```

2. **Run the Docker Container:**

   ```bash
   docker run -d -p 5000:5000 --name blog-demo-container blog-demo
   ```

3. **Access the Application:**

   Open your browser and navigate to [http://localhost:5000](http://localhost:5000).

_Note:_ Ensure that you have configured the necessary environment variables in your Docker environment (either via a `.env` file copied into the container or using Docker environment variable options).

### Security

- **Password Security:** Passwords are hashed using secure algorithms.
- **Multi-Factor Authentication:** MFA is enforced for additional security.
- **Encryption of Posts:** Each post’s title and body are encrypted using a unique key derived from the user's password and salt.
- **Web Application Firewall (WAF):** Basic patterns are used to filter SQL injection, XSS, and path traversal attacks.
- **Rate Limiting:** Login and registration endpoints are rate-limited to prevent brute-force attacks.

### Logging

All critical actions (registration, login, post creation, updates, and deletions) are logged with timestamps, user emails, roles, and IP addresses in the `logs.log` file. This ensures auditability and helps in monitoring potential security issues.

### API Endpoints

- **POST /api/accounts/register:** User registration endpoint.
- **POST /api/accounts/login:** User login with MFA verification.
- **POST /api/accounts/logout:** Log out the current user.
- **GET /api/accounts/account:** Retrieve current user account details and posts.
- **GET /api/accounts/setup_mfa:** Get MFA key and QR code for setup.
- **POST /api/accounts/unlock:** Unlock a user account (admin-only).

### License

This project is licensed under the MIT License.

