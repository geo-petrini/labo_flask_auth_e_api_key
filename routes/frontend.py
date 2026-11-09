import re

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from models.conn import db
from models.model import Role, Series, User
from worker import enqueue_series, validate_series_input


frontend_bp = Blueprint('frontend', __name__)

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


@frontend_bp.route("/")
def home():
    return render_template('default.html')


@frontend_bp.route('/series')
@login_required
def series_history():
    """Elenco delle serie richieste dall'utente corrente."""
    series_list = (
        Series.query
        .filter_by(user_id=current_user.id)
        .order_by(Series.created_at.desc(), Series.id.desc())
        .all()
    )
    return render_template('series/history.html', series_list=series_list)


@frontend_bp.route('/series/new', methods=['GET', 'POST'])
@login_required
def series_input():
    """Input di una nuova serie da calcolare."""
    if request.method == 'POST':
        expression = (request.form.get('expression') or '').strip()

        try:
            start = int(request.form.get('start'))
            end = int(request.form.get('end'))
        except (TypeError, ValueError):
            flash('Inizio e fine devono essere numeri interi.', 'danger')
            return render_template('series/new.html')

        try:
            expression, start, end = validate_series_input(expression, start, end)
        except ValueError as exc:
            flash(str(exc), 'danger')
            return render_template('series/new.html')

        series = Series(
            user_id=current_user.id,
            expression=expression,
            start=start,
            end=end,
            status=Series.STATUS_PENDING,
        )
        db.session.add(series)
        db.session.commit()

        enqueue_series(series.id)
        flash('Serie accodata: il calcolo è in corso.', 'info')
        return redirect(
            url_for('frontend.series_output', series_id=series.id)
        )

    return render_template('series/new.html')


@frontend_bp.route('/series/<int:series_id>')
@login_required
def series_output(series_id):
    """Output/risultato di una serie calcolata."""
    series = db.session.get(Series, series_id)
    if series is None:
        abort(404)

    # Un utente può vedere solo le proprie serie; gli admin vedono tutto.
    if series.user_id != current_user.id and not current_user.is_admin:
        abort(404)

    return render_template(
        'series/result.html',
        series=series,
        result=series.result,
        series_id=series.id,
    )


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
