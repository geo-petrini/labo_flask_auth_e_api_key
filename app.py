from flask import Flask
from flask_migrate import Migrate

from config import Config
from models.conn import db
from models.model import Role, User, seed_admin
from routes.admin import admin_bp
from routes.api import api_bp
from routes.frontend import frontend_bp


migrate = Migrate()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(frontend_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)

    @app.shell_context_processor
    def shell_context():
        return {'db': db, 'User': User, 'Role': Role}

    @app.cli.command('seed')
    def seed():
        """Populate roles and the admin user."""
        seed_admin()
        print('Database seeded')

    return app


app = create_app()


if __name__ == '__main__':
    app.run(debug=True)
