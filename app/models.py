from app import db 
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy.dialects.postgresql import ARRAY


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
    stored_filename = db.Column(db.String(200), unique=True, nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    description = db.Column(db.Text)
    tags = db.Column(ARRAY(db.String()))
    genre = db.Column(db.String(120))

    image_metadata = db.relationship("ImageMetadata", backref="file", uselist=False, cascade="all, delete-orphan")
    video_metadata = db.relationship("VideoMetadata", backref="file", uselist=False, cascade="all, delete-orphan")
    audio_metadata = db.relationship("AudioMetadata", backref="file", uselist=False, cascade="all, delete-orphan")

    def _metadata_dict(self):
        if self.image_metadata:
            return {
                "type": "image",
                "width": self.image_metadata.width,
                "height": self.image_metadata.height,
                "color_depth": self.image_metadata.color_depth,
                "dpi": self.image_metadata.dpi,
                "exif": self.image_metadata.exif,
            }

        if self.video_metadata:
            return {
                "type": "video",
                "duration": self.video_metadata.duration,
                "width": self.video_metadata.width,
                "height": self.video_metadata.height,
                "fps": self.video_metadata.fps,
                "codec": self.video_metadata.codec,
                "bitrate": self.video_metadata.bitrate,
                "versions": {
                    "1080p": self.video_metadata.version_1080p_path,
                    "720p": self.video_metadata.version_720p_path,
                    "480p": self.video_metadata.version_480p_path,
                }
            }

        if self.audio_metadata:
            return {
                "type": "audio",
                "duration": self.audio_metadata.duration,
                "bitrate": self.audio_metadata.bitrate,
                "sample_rate": self.audio_metadata.sample_rate,
                "channels": self.audio_metadata.channels
            }

        return None


class ImageMetadata(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'), nullable=False, unique=True)

    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    color_depth = db.Column(db.Text)
    dpi = db.Column(db.Integer)
    exif = db.Column(db.JSON)

    thumbnail_path = db.Column(db.String(300))


class VideoMetadata(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'), nullable=False, unique=True)

    duration = db.Column(db.Float)
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    fps = db.Column(db.Float)
    codec = db.Column(db.String(50))
    bitrate = db.Column(db.Integer)

    thumbnail_path = db.Column(db.String(300))

    version_1080p_path = db.Column(db.String(300))
    version_720p_path = db.Column(db.String(300))
    version_480p_path = db.Column(db.String(300))


class AudioMetadata(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'), nullable=False, unique=True)

    duration = db.Column(db.Float)
    bitrate = db.Column(db.Integer)
    sample_rate = db.Column(db.Integer)
    channels = db.Column(db.Integer)