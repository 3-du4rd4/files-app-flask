from app import db 
from flask_login import UserMixin
from datetime import datetime



class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    profile_image = db.Column(db.String(200))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    files = db.relationship('File', backref='owner', lazy=True) 


class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(200), nullable=False)
    stored_filename = db.Column(db.String(200), unique=True, nullable=False) # Nome único no disco
    file_type = db.Column(db.String(50), nullable=False) # MIME Type
    file_size = db.Column(db.Integer, nullable=False) # Tamanho em bytes
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    # Chave estrangeira para o usuário que fez o upload
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
