from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from models.model import Role, User


admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# before_request è un hook di Flask: viene eseguito prima di ogni view
# registrata su questo blueprint. Qui lo usiamo per proteggere in un solo
# punto tutte le route /admin, comprese quelle che aggiungeremo in futuro.
#
# I decoratori si applicano dal basso verso l'alto:
# 1. login_required avvolge require_admin e, se l'utente non è autenticato,
#    restituisce un redirect al login aggiungendo ?next=<url richiesto>;
# 2. before_request registra la funzione così ottenuta come hook del blueprint.
#
# Una view può restituire None per lasciare proseguire la richiesta, oppure
# una Response (ad esempio un redirect) per interromperla. Se l'utente è
# autenticato ma non è admin, restituiamo il redirect alla home.
@admin_bp.before_request
@login_required
def require_admin():
    if not current_user.is_admin:
        flash('Accesso riservato agli amministratori.', 'danger')
        return redirect(url_for('frontend.home'))


# Qui non serve un decoratore aggiuntivo sulla dashboard: il controllo è già
# stato eseguito da require_admin prima che questa funzione venga chiamata.
# Un decoratore @admin_required sulle singole view sarebbe l'alternativa se
# volessimo proteggere solo alcune route o avere permessi diversi per route.


@admin_bp.route('')
def dashboard():
    total_users = User.query.count()
    total_admins = User.query.filter_by(is_admin=True).count()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()

    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        total_admins=total_admins,
        total_regular_users=total_users - total_admins,
        total_roles=Role.query.count(),
        recent_users=recent_users,
    )


@admin_bp.route('/users')
def users():
    all_users = User.query.order_by(User.username).all()
    return render_template('admin/users.html', users=all_users)
