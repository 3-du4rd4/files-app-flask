from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, db
import os

bp = Blueprint('main', __name__)

@bp.route('/')
def home():
    return redirect(url_for('main.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('User already exists', 'danger')
            return redirect(url_for('main.register'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, full_name=full_name, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        desc = request.form['description']

        current_user.full_name = request.form['full_name']
        current_user.email = request.form['email']
        current_user.description = desc if desc.strip() != "" else None

        if request.form.get('password'):
            current_user.password = generate_password_hash(request.form['password'])

        if 'profile_image' in request.files:
            image = request.files['profile_image']
            if image.filename != '':
                image.save(os.path.join('app/static/profile_pics', image.filename))
                current_user.profile_image = image.filename

        db.session.commit()
        return redirect(url_for('main.dashboard'))

    return render_template('edit_profile.html', user=current_user)
