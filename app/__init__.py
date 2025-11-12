from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from datetime import datetime
import os

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    from app import routes
    app.register_blueprint(routes.bp)

    with app.app_context():
        db.create_all()

    return app
