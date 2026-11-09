import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from models.conn import db
from models.model import Role, User


frontend_bp = Blueprint('frontend', __name__)

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


@frontend_bp.route("/")
def home():
    return render_template('default.html')


@frontend_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('frontend.home'))

    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        confirm_password = request.form.get('confirm_password') or ''

        errors = []
        if not username:
            errors.append('Lo username è obbligatorio.')
        elif not 3 <= len(username) <= 80:
            errors.append('Lo username deve contenere da 3 a 80 caratteri.')

        if not email:
            errors.append("L'email è obbligatoria.")
        elif not EMAIL_RE.match(email):
            errors.append('Inserisci un indirizzo email valido.')

        if len(password) < 8:
            errors.append('La password deve contenere almeno 8 caratteri.')
        if password != confirm_password:
            errors.append('Le password non coincidono.')

        if username and User.query.filter(
            func.lower(User.username) == username.lower()
        ).first():
            errors.append('Username già in uso.')
        if email and User.query.filter(
            func.lower(User.email) == email.lower()
        ).first():
            errors.append('Email già registrata.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template(
                'register.html', username=username, email=email
            )

        role = Role.query.filter_by(role_name='user').first()
        if role is None:
            role = Role(role_name='user')
            db.session.add(role)

        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('Username o email già in uso.', 'danger')
            return render_template(
                'register.html', username=username, email=email
            )

        flash('Registrazione completata. Ora puoi effettuare il login.', 'success')
        return redirect(url_for('frontend.login'))

    return render_template('register.html')


@frontend_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('frontend.home'))

    if request.method == 'POST':
        identifier = (request.form.get('identifier') or '').strip()
        password = request.form.get('password') or ''
        remember = request.form.get('remember') == 'on'

        user = None
        if identifier:
            user = User.query.filter(
                (func.lower(User.username) == identifier.lower()) |
                (func.lower(User.email) == identifier.lower())
            ).first()

        if user is None or not user.check_password(password):
            flash('Credenziali non valide.', 'danger')
            return render_template('login.html', identifier=identifier)

        login_user(user, remember=remember)
        flash(f'Benvenuto, {user.username}!', 'success')

        next_page = request.args.get('next')
        if next_page and next_page.startswith('/') and not next_page.startswith('//'):
            return redirect(next_page)
        return redirect(url_for('frontend.home'))

    return render_template('login.html')


@frontend_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout effettuato.', 'info')
    return redirect(url_for('frontend.home'))
