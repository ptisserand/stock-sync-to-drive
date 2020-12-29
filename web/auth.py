from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required

from werkzeug.security import check_password_hash
from .models import User
from .models import db
import logging

logger = logging.getLogger("auth")
auth = Blueprint('auth', __name__)


def check_login(email, password, remember=False) -> bool:
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        return False
    else:
        login_user(user, remember=remember)
        return True

@auth.route('/api/login', methods=['POST'])
def login_api():
    payload = request.get_json()
    email = payload.get('email', None)
    password = payload.get('password', None)
    is_ok = check_login(email, password)
    if not is_ok:
        response = jsonify({'error': 'wrong username or password'})
        return response, 401
    else:
        return jsonify({'message': 'welcome!'})

@auth.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')    
    remember = True if request.form.get('remember') else False

    is_ok = check_login(email, password, remember)
    if not is_ok:
        flash('Please check your login details and try again.')
        logger.warning(f"Connection failed for {email}")
        return redirect(url_for('auth.login')) # if the user doesn't exist or password is wrong, reload the page
    else:
        # if the above check passes, then we know the user has the right credentials
        return redirect(url_for('main.index'))

@auth.route('/login')
def login():
    return render_template('login.html')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

