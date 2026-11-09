from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate

from config import Config
from models.conn import db
from models.model import ApiKey, Role, Series, User, seed_admin
from routes.admin import admin_bp
from routes.api import api_bp
from routes.frontend import frontend_bp
from worker import start_worker


migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'frontend.login'
login_manager.login_message = 'Effettua il login per continuare.'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    app.register_blueprint(frontend_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)

    # In questa fase il calcolo gira in un thread dentro il processo Flask.
    # START_WORKER permette di disattivarlo (es. nei test o nei comandi CLI).
    if app.config.get('START_WORKER', True):
        start_worker(app)

    @app.cli.command('seed')
    def seed():
        """Populate roles and the admin user."""
        seed_admin()
        print('Database seeded')

    return app


app = create_app()


if __name__ == '__main__':
    app.run(debug=True)
