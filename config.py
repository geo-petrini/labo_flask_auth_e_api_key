import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///storage.sqlite')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Avvia il thread worker in-process (disattivabile con START_WORKER=0).
    START_WORKER = os.environ.get('START_WORKER', '1') != '0'
