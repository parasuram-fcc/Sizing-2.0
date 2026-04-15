import secrets
from functools import wraps

from flask import request, redirect, url_for, render_template, flash, session, jsonify, abort
from flask_login import login_user, logout_user, current_user
from sqlalchemy import desc
from werkzeug.security import generate_password_hash, check_password_hash

from app.blueprints.auth import bp
from app.blueprints.auth.helpers import send_otp, add_user_as_engineer, create_default_project_and_item
from app.extensions import db, login_manager, oauth
from app.forms.auth import LoginForm, RegisterForm, EmailOTPForm, ResetPasswordRequestForm, ResetPasswordForm
from app.models import (
    userMaster, OTP, designationMaster, departmentMaster,
    projectMaster, itemMaster,
)
from app.utils.helpers import error_handler


# ---------------------------------------------------------------------------
# Flask-Login: user loader callback
# ---------------------------------------------------------------------------

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(userMaster, int(user_id))


# ---------------------------------------------------------------------------
# Admin-only decorator
# WARNING: userMaster.query.filter(admin=True) is invalid SQLAlchemy syntax
# and would raise an error at runtime. This decorator is not applied to any
# route — leaving untouched to avoid changing business logic.
# ---------------------------------------------------------------------------

def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin = userMaster.query.filter(admin=True).all()
        admin_id = [i.id for i in admin]
        if current_user.id not in admin_id:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function


# ===========================================================================
# AUTH ROUTES
# All routes are prefixed with /auth (defined in blueprint __init__.py)
# ===========================================================================

# ---------------------------------------------------------------------------
# Registration - Step 1: Email OTP verification
# Route: GET/POST /auth/email-otp
# ---------------------------------------------------------------------------

@bp.route('/email-otp', methods=["GET", "POST"])
@error_handler
def emailOTP():
    form = EmailOTPForm()
    if request.method == 'POST':
        email_ = request.form.get('email')
        otp_ = request.form.get('otp')
        otp_element = db.session.query(OTP).filter_by(username=email_).first()
        if otp_element and int(otp_element.otp) == int(otp_):
            session['email'] = email_
            return redirect(url_for('auth.register'))
        else:
            flash('Incorrect OTP', 'failure')
            return render_template("auth/email-otp.html", form=form, default_email=email_)
    return render_template("auth/email-otp.html", form=form, default_email='')


# ---------------------------------------------------------------------------
# Registration - Step 2: Create account
# Route: GET/POST /auth/admin-register
# ---------------------------------------------------------------------------

@bp.route('/admin-register', methods=["GET", "POST"])
@error_handler
def register():
    email = session.get('email')
    form = RegisterForm()
    designations_ = designationMaster.query.all()
    departments_ = departmentMaster.query.all()

    # Load existing names for duplicate-name client-side check
    names_ = [u.name for u in userMaster.query.with_entities(userMaster.name).all()]

    if request.method == "POST":
        if userMaster.query.filter_by(email=request.form['email']).first():
            flash("Email-ID already exists", "failure")
            return redirect(url_for('auth.register', email=email))

        department_element = departmentMaster.query.get(int(request.form['department']))
        designation_element = designationMaster.query.get(int(request.form['designation']))

        new_user = userMaster(
            email=request.form['email'],
            password=generate_password_hash(
                request.form['password'], method='pbkdf2:sha256', salt_length=8
            ),
            name=request.form['name'],
            initial=request.form['initial'],
            employeeId=None,
            mobile=request.form['mobile'],
            designation=designation_element,
            department=department_element,
        )
        new_user.fccUser = request.form['email'].split('@')[-1] == 'fccommune.com'

        db.session.add(new_user)
        db.session.commit()
        add_user_as_engineer(request.form['name'], designation_element.name)
        create_default_project_and_item(user=new_user)
        return redirect(url_for('auth.login'))

    return render_template(
        "auth/admin-registration.html",
        form=form, names_=names_, email=email,
        designations=designations_, departments=departments_,
    )


# ---------------------------------------------------------------------------
# Google OAuth - Step 1: Initiate login
# Route: GET /auth/login/google
# ---------------------------------------------------------------------------

@bp.route('/login/google')
def login_google():
    redirect_uri = url_for("auth.auth_google", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


# ---------------------------------------------------------------------------
# Google OAuth - Step 2: Callback handler
# Route: GET /auth/google
# ---------------------------------------------------------------------------

@bp.route('/google')
@error_handler
def auth_google():
    token = oauth.google.authorize_access_token(leeway=300)
    session["access_token"] = token.get("access_token")

    resp = oauth.google.get("https://openidconnect.googleapis.com/v1/userinfo")
    user_info = resp.json()

    generated_password = secrets.token_hex(8)

    user_data = {
        "provider": "google",
        "id": user_info.get("sub"),
        "name": user_info.get("name"),
        "initial": user_info.get("initial"),
        "email": user_info.get("email"),
        "access_token": token.get("access_token"),
        "password": generated_password,
    }

    existing = userMaster.query.filter_by(email=user_data["email"]).first()
    if not existing:
        code = user_data["name"][0] + user_data["name"][-1]
        new_user = userMaster(
            name=user_data["name"],
            initial=user_data["name"][-1],
            code=code,
            email=user_data["email"],
            fccUser=False,
            password=user_data["password"],
        )
        db.session.add(new_user)
        db.session.commit()
        user = new_user
        create_default_project_and_item(user=user)
    else:
        user = existing

    login_user(user)
    user.login_count = (user.login_count or 0) + 1
    db.session.commit()

    project_element = db.session.query(projectMaster).filter_by(
        user=current_user
    ).order_by(desc(projectMaster.id)).first()

    if not project_element:
        flash("Welcome! Please create your first project.", "success")
        return redirect(url_for('create_project'))  # TODO: update to project blueprint endpoint when available

    item_element = db.session.query(itemMaster).filter_by(project=project_element).first()
    if not item_element:
        flash("Please create your first item.", "info")
        return redirect(url_for('create_item', proj_id=project_element.id))  # TODO: update to project blueprint endpoint when available

    return redirect(url_for('home', proj_id=project_element.id, item_id=item_element.id))  # TODO: update to home blueprint endpoint when available


# ---------------------------------------------------------------------------
# Login
# Route: GET/POST /auth/login
# ---------------------------------------------------------------------------

@bp.route('/login', methods=["GET", "POST"])
@error_handler
def login():
    form = LoginForm()
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:
            flash("Please provide both email and password.", "failure")
            return redirect(url_for('auth.login'))

        user = userMaster.query.filter_by(email=email).first()
        if not user:
            flash("Email does not exist, please try again.", "failure")
            return redirect(url_for('auth.login'))

        if not check_password_hash(user.password, password):
            flash("Password incorrect, please try again.", "failure")
            return redirect(url_for('auth.login'))

        login_user(user)

        # Hardcoded admin grant for a specific account — preserving existing behavior
        if user.email == 'devayani@fccommune.com':
            user.admin = True
            db.session.commit()

        current_user.login_count = (current_user.login_count or 0) + 1
        db.session.commit()

        return redirect(url_for('home.home', proj_id=None, item_id=None))  # TODO: update to home blueprint endpoint when available

    return render_template("auth/login.html", form=form)


# ---------------------------------------------------------------------------
# Guest login (no account required)
# Route: GET /auth/guest-login
# ---------------------------------------------------------------------------

@bp.route('/guest-login')
@error_handler
def guest_login():
    session.clear()
    session["guest"] = True
    session["guest_project"] = {
        "id": "GUEST",
        "l_flowrate_type": "mass",
        "trim_exit_velocity": "no",
    }
    session["guest_item"] = {
        "id": "GUEST",
        "project": session["guest_project"],
        "standardStatus": True,
        "pipeDataStatus": True,
        "inpipe_unit": 1,
        "outpipe_unit": 1,
        "flowrate_unit": 1,
    }
    session["guest_cases"] = [{}]
    session["guest_valve"] = [{}]
    return redirect(url_for("valveSizing"))  # TODO: update to valve_sizing blueprint endpoint when available


# ---------------------------------------------------------------------------
# Logout
# Route: GET /auth/logout
# ---------------------------------------------------------------------------

@bp.route('/logout')
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('auth.login'))


# ---------------------------------------------------------------------------
# Password reset - Step 1: Enter email, receive OTP
# Route: GET/POST /auth/reset-pw
# ---------------------------------------------------------------------------

@bp.route('/reset-pw', methods=["GET", "POST"])
@error_handler
def resetPassword():
    form = ResetPasswordRequestForm()
    if request.method == 'POST':
        email_ = request.form.get('email')
        if userMaster.query.filter_by(email=email_).first():
            otp_sent, otp_msg = send_otp(email_)
            if otp_sent:
                session['reset-email'] = email_
                return redirect(url_for('auth.sendOTPEmail'))
            else:
                flash(f'Something went wrong: {otp_msg}', 'failure')
                return redirect(url_for('auth.resetPassword'))
        else:
            flash('Email is not recognized', 'failure')
    return render_template('auth/send-email-otp.html', form=form)


# ---------------------------------------------------------------------------
# Password reset - Step 2: AJAX endpoint — check email exists and send OTP
# Route: GET /auth/send_otp
# Response keys preserved for backward compatibility with email-otp.js
# ---------------------------------------------------------------------------

@bp.route('/send_otp', methods=["GET", "POST"])
@error_handler
def sendOTPAjax():
    emailID = request.args.get('emailID', '').strip()
    if userMaster.query.filter_by(email=emailID).first():
        return jsonify({'message': 'User already exist'})
    otp_sent, message = send_otp(emailID)
    # if :
        # return jsonify({'message': 'OTP Sent'})
    return jsonify({'status':'success' if otp_sent else 'error', 'message': message})


# ---------------------------------------------------------------------------
# Password reset - Step 3: Verify OTP and set new password
# Route: GET/POST /auth/send-otp
#
# KNOWN BUG (pre-existing, not modified): `username` and `otp_` are assigned
# only inside the POST block, but `otp_element` is queried outside it.
# A direct GET request to this URL will raise UnboundLocalError.
# This route is only ever reached via a POST-triggered redirect from
# resetPassword(), so in normal flow GET never hits this directly.
# ---------------------------------------------------------------------------

@bp.route('/send-otp', methods=["GET", "POST"])
@error_handler
def sendOTPEmail():
    form = ResetPasswordForm()
    email = session.get('reset-email')
    if request.method == 'POST':
        otp_ = request.form['otp']
        username = email
        otp_element = db.session.query(OTP).filter_by(username=username).first()
        if int(otp_element.otp) == int(otp_):
            user_element = db.session.query(userMaster).filter_by(email=username).first()
            user_element.password = generate_password_hash(
                request.form['password'], method='pbkdf2:sha256', salt_length=8
            )
            db.session.commit()
            flash('Password Reset Successfully', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Incorrect OTP', 'failure')
    return render_template('auth/reset-pw.html', form=form, email=email)
