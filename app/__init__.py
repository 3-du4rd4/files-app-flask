from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from datetime import datetime
from dotenv import load_dotenv
import os

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    load_dotenv()

    key = os.getenv('SECRET_KEY')
    database_url = os.getenv('DATABASE_URL')

    print(f"SECRET_KEY: {key}")
    print(f"DATABASE_URL: {database_url}")

    app.config['SECRET_KEY'] = key
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    from app import routes
    app.register_blueprint(routes.bp)

    with app.app_context():
        db.create_all()

    return app
