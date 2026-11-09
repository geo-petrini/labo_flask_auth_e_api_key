from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from models.model import Role, User


admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.before_request
@login_required
def require_admin():
    if not current_user.is_admin:
        flash('Accesso riservato agli amministratori.', 'danger')
        return redirect(url_for('frontend.home'))


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
