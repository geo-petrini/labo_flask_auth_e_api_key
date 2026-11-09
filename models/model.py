import os
import secrets

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


class Series(db.Model):
    """Una serie richiesta da un utente e il suo stato di calcolo."""

    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_DONE = 'done'
    STATUS_ERROR = 'error'

    STATUS_LABELS = {
        STATUS_PENDING: 'In attesa',
        STATUS_RUNNING: 'In calcolo',
        STATUS_DONE: 'Completata',
        STATUS_ERROR: 'Errore',
    }

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    expression = db.Column(db.String(500), nullable=False)
    start = db.Column(db.Integer, nullable=False)
    end = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING)
    result = db.Column(db.Float, nullable=True)
    error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=func.now())
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship(
        'User', backref=db.backref('series', lazy='select', cascade='all, delete-orphan')
    )

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, self.status)

    @property
    def is_finished(self):
        return self.status in (self.STATUS_DONE, self.STATUS_ERROR)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'expression': self.expression,
            'start': self.start,
            'end': self.end,
            'status': self.status,
            'result': self.result,
            'error': self.error,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
        }


class ApiKey(db.Model):
    """Chiave API di un utente. Un utente può averne al massimo una."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True
    )
    key = db.Column(db.String(128), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=func.now())

    user = db.relationship(
        'User', backref=db.backref('api_key', uselist=False)
    )

    @staticmethod
    def generate_key():
        return 'sk_' + secrets.token_urlsafe(32)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'key': self.key,
            'created_at': self.created_at.isoformat() if self.created_at else None,
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
