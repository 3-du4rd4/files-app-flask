import os
from datetime import timedelta 
from dotenv import load_dotenv
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager 
from flask import Flask, redirect, url_for


db = SQLAlchemy()
jwt = JWTManager() 
migrate = Migrate()


def create_app():
    app = Flask(__name__)

    load_dotenv()

    key = os.getenv('SECRET_KEY')
    database_url = os.getenv('DATABASE_URL')
    
    app.config['SECRET_KEY'] = key
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    

    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=30) 
    app.config["JWT_SECRET_KEY"] = key 
    

    app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
    

    app.config["JWT_HEADER_NAME"] = ""
    app.config["JWT_QUERY_STRING_NAME"] = ""
    app.config["JWT_JSON_KEY"] = ""
    app.config["JWT_ERROR_MESSAGE_KEY"] = "message"

    app.config["JWT_COOKIE_SECURE"] = False        
    app.config["JWT_COOKIE_SAMESITE"] = "Lax"      
    app.config["JWT_ACCESS_COOKIE_PATH"] = "/"
    app.config["JWT_COOKIE_HTTPONLY"] = True       
    app.config["JWT_COOKIE_CSRF_PROTECT"] = False  
    

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app) 

    @jwt.unauthorized_loader
    def unauthorized_callback(callback):
        return redirect(url_for('main.login'))

    from app import routes
    app.register_blueprint(routes.bp)

    with app.app_context():
        db.create_all()

    return app
