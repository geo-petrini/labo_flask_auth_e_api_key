import os

from flask_login import UserMixin

from models.conn import db
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(260), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    created_at = db.Column(db.DateTime, nullable=False, default=func.now())

    role = db.relationship('Role', backref=db.backref('users', lazy='select'))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_role(self, role_name):
        return self.role is not None and self.role.role_name == role_name

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_admin': self.is_admin,
            'role': self.role.to_dict() if self.role else None,
        }


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(120), nullable=False, unique=True)

    def to_dict(self):
        return {
            'id': self.id,
            'role_name': self.role_name,
        }


def seed_admin():
    """Create the admin/user roles and the default admin user (idempotent)."""
    admin_username = os.getenv('SEED_ADMIN_USERNAME', 'admin')
    admin_email = os.getenv('SEED_ADMIN_EMAIL', 'admin@example.com')
    admin_password = os.getenv('SEED_ADMIN_PASSWORD', 'admin123')

    admin_role = Role.query.filter_by(role_name='admin').first()
    if admin_role is None:
        admin_role = Role(role_name='admin')
        db.session.add(admin_role)

    if Role.query.filter_by(role_name='user').first() is None:
        db.session.add(Role(role_name='user'))

    admin = User.query.filter_by(username=admin_username).first()
    if admin is None:
        admin = User.query.filter_by(email=admin_email).first()

    if admin is None:
        admin = User(username=admin_username, email=admin_email)
        admin.set_password(admin_password)
        db.session.add(admin)

    admin.is_admin = True
    admin.role = admin_role

    db.session.commit()
    return admin
