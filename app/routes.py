import os
import json
import uuid 
import banco
import s3_handle
from app import db
from io import BytesIO
from sqlalchemy import or_, func
from werkzeug.utils import secure_filename
from flask_jwt_extended import jwt_required
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import unset_jwt_cookies 
from flask_jwt_extended import set_access_cookies
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import AudioMetadata, ImageMetadata, User, VideoMetadata, db, File
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, make_response


ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

s3 = s3_handle.load_s3(ACCESS_KEY_ID, SECRET_ACCESS_KEY)

userDAO = banco.UserDAO(db)
filesDAO = banco.FilesDAO(db)

bp = Blueprint('main', __name__)


def save_to_s3(file, user_id, original_filename):
    unique_id = str(uuid.uuid4())[:8]
    extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    stored_filename = f"users/{user_id}/{unique_id}-{original_filename}"
    
    file_copy = BytesIO(file.read())
    file.seek(0) 
    
    file_copy.seek(0)
    s3.upload_fileobj(file_copy, s3_handle.BUCKET_NAME, stored_filename)
    
    return stored_filename


def delete_file_from_s3(stored_filename, metadata=None):
    s3.delete_object(Bucket=s3_handle.BUCKET_NAME, Key=stored_filename)

    if metadata and hasattr(metadata, "thumbnail_path") and metadata.thumbnail_path:
        s3.delete_object(Bucket=s3_handle.BUCKET_NAME, Key=metadata.thumbnail_path)
    
    if metadata and isinstance(metadata, VideoMetadata):
        for path in [metadata.version_1080p_path, metadata.version_720p_path, metadata.version_480p_path]:
            if path:
                s3.delete_object(Bucket=s3_handle.BUCKET_NAME, Key=path)


def get_user_id_from_jwt():
    user_id_str = get_jwt_identity()
    try:
        return int(user_id_str)
    except (TypeError, ValueError):
        return None


@bp.route('/')
def home():
    return redirect(url_for('main.login'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']

        existing_user = userDAO.user_by_username(username)

        if existing_user:
            flash('User already exists', 'danger')
            return redirect(url_for('main.register'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, full_name=full_name, email=email, password=hashed_password)

        userDAO.create_user(new_user)

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html')



@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = userDAO.user_by_username(username)

        if user and check_password_hash(user.password, password):

            access_token = create_access_token(identity=str(user.id))
            response = make_response(redirect(url_for('main.dashboard')))

            set_access_cookies(response, access_token)
            
            flash(f'Login successful!', 'success')
            return response
        
        flash('Invalid username or password', 'danger')
        
    return render_template('login.html')


@bp.route('/logout')
def logout():
    response = make_response(redirect(url_for('main.login')))
    unset_jwt_cookies(response)
    flash('You have been logged out.', 'info')
    return response


@bp.route('/dashboard', methods=['GET', 'POST'])
@jwt_required() 
def dashboard():
    user_id = get_user_id_from_jwt()
    if user_id is None:
        return redirect(url_for('main.logout'))

    current_user = userDAO.user_by_id(user_id)

    if request.method == 'POST':
        if 'file_to_upload' not in request.files or request.files['file_to_upload'].filename == '':
            flash('Nenhum arquivo selecionado.', 'danger')
            return redirect(request.url)

        file = request.files['file_to_upload']
        tags_json = request.form.get("tags")
        tags = json.loads(tags_json) if tags_json else []
        description = request.form.get('description', '').strip()
        genre = request.form.get('genre')
        genre = genre.strip() if genre else None

        if file:
            try:
                file_content = file.read()
                file.seek(0) 
                
                file_obj = BytesIO(file_content)
                file_obj.seek(0)
                
                stored_filename = save_to_s3(file_obj, user_id, file.filename)
                
                file_obj.seek(0)
                
                new_file = File(
                    original_filename=file.filename,
                    stored_filename=stored_filename,
                    file_type=file.content_type,
                    file_size=len(file_content),
                    description=description,
                    tags=tags,
                    genre=genre,
                    user_id=user_id
                )
                
                filesDAO.insert_file(new_file)

                # --------------------- PROCESSAMENTO POR TIPO ---------------------
                
                # IMAGEM
                if file.content_type.startswith("image"):
                    from app.processors.image_processor import processar_imagem
                    
                    img_copy = BytesIO(file_content)
                    img_copy.seek(0)
                    info, thumb_bytes = processar_imagem(img_copy)
                    
                    thumbnail_key = stored_filename.replace("users/", "users/thumbnails/")
                    thumb_io = BytesIO(thumb_bytes)
                    thumb_io.seek(0)
                    s3.upload_fileobj(thumb_io, s3_handle.BUCKET_NAME, thumbnail_key)
                    
                    metadata = ImageMetadata(
                        file_id=new_file.id,
                        width=info.get("largura"),
                        height=info.get("altura"),
                        color_depth=info.get("profundidade_cor"),
                        dpi=info.get("dpi"),
                        exif=info.get("exif"),
                        thumbnail_path=thumbnail_key
                    )
                    db.session.add(metadata)

                # VÍDEO
                elif file.content_type.startswith("video"):
                    from app.processors.video_processor import processar_video
                    
                    video_copy = BytesIO(file_content)
                    video_copy.seek(0)
                    info, thumb_bytes, versions = processar_video(video_copy)
                    
                    thumbnail_key = stored_filename.replace("users/", "users/thumbnails/")
                    thumb_io = BytesIO(thumb_bytes)
                    thumb_io.seek(0)
                    s3.upload_fileobj(thumb_io, s3_handle.BUCKET_NAME, thumbnail_key)
                    
                    version_keys = {}
                    for res, version_data in versions.items():
                        version_key = stored_filename.replace("users/", f"users/versions/{res}/")
                        version_io = BytesIO(version_data)
                        version_io.seek(0)
                        s3.upload_fileobj(version_io, s3_handle.BUCKET_NAME, version_key)
                        version_keys[f"version_{res}_path"] = version_key
                    
                    metadata = VideoMetadata(
                        file_id=new_file.id,
                        duration=info.get("duracao_segundos"),
                        width=info.get("largura"),
                        height=info.get("altura"),
                        fps=info.get("fps"),
                        codec=info.get("codec_video"),
                        bitrate=info.get("bitrate"),
                        thumbnail_path=thumbnail_key,
                        **version_keys
                    )
                    db.session.add(metadata)

                # ÁUDIO
                elif file.content_type.startswith("audio"):
                    from app.processors.audio_processor import processar_audio
                    audio_copy = BytesIO(file_content)
                    audio_copy.seek(0)
                    info = processar_audio(audio_copy)
                    
                    metadata = AudioMetadata(
                        file_id=new_file.id,
                        duration=info.get("duracao_segundos"),
                        bitrate=info.get("bitrate"),
                        sample_rate=info.get("sample_rate"),
                        channels=info.get("channels"),
                    )
                    db.session.add(metadata)

                db.session.commit()
                flash(f'Arquivo "{file.filename}" carregado com sucesso!', 'success')

            except Exception as e:
                db.session.rollback()
                flash(f'Ocorreu um erro durante o upload do arquivo: {str(e)}', 'danger')

            return redirect(url_for('main.dashboard'))

    # ------------------- Lógica GET -------------------
    search_query = request.args.get('search', '').strip()
    query = File.query.filter_by(user_id=user_id)

    if search_query:
        sq = f"%{search_query}%"
        query = query.filter(or_(
            File.original_filename.ilike(sq),
            File.file_type.ilike(sq),
            File.tags.any(func.lower(search_query))
        ))

    user_files = query.order_by(File.upload_date.desc()).all()

    def generate_presigned_url(key, expiration=3600):
        if not key:
            return None
        return s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': s3_handle.BUCKET_NAME, 'Key': key},
            ExpiresIn=expiration
        )

    files_with_thumbs = []
    for f in user_files:
        thumb_url = None
        if f.file_type.startswith("image") and hasattr(f, 'image_metadata') and f.image_metadata:
            thumb_url = generate_presigned_url(f.image_metadata.thumbnail_path)
        elif f.file_type.startswith("video") and hasattr(f, 'video_metadata') and f.video_metadata:
            thumb_url = generate_presigned_url(f.video_metadata.thumbnail_path)
        
        files_with_thumbs.append({
            "id": f.id,
            "original_filename": f.original_filename,
            "file_type": f.file_type,
            "file_size": f.file_size,
            "upload_date": f.upload_date,
            "description": f.description,
            "tags": f.tags,
            "thumb_url": thumb_url
        })

    profile_url = generate_presigned_url(current_user.profile_image) if current_user.profile_image else None

    return render_template('dashboard.html', user=current_user, files=files_with_thumbs, search_query=search_query, profile_url=profile_url)


@bp.route('/view_file/<int:file_id>')
@jwt_required()
def view_file(file_id):
    user_id = get_user_id_from_jwt()

    if user_id is None:
        return redirect(url_for('main.logout'))

    file_record = filesDAO.query_file_by_id(file_id)
    
    if file_record.user_id != user_id: 
        flash('Você não tem permissão para visualizar este arquivo.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    def generate_presigned_url(key, expiration=3600):
        return s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': s3_handle.BUCKET_NAME, 'Key': key},
            ExpiresIn=expiration
        )

    file_url = generate_presigned_url(file_record.stored_filename)
    file_metadata = file_record._metadata_dict()

    video_versions = None

    if file_metadata and file_metadata.get("type") == "video":
        versions = file_metadata.get("versions", {}) 
        
        video_versions = {
            quality: generate_presigned_url(path)
            for quality, path in versions.items()
        }

        print("Video Versions URLs:", video_versions)

    return render_template('view_media.html', file={
        "obj": file_record,
        "file_url": file_url,
        "metadata": file_metadata,
        "video_versions": video_versions
    }, user=userDAO.user_by_id(user_id))


@bp.route('/rename_file/<int:file_id>', methods=['POST'])
@jwt_required()
def rename_file(file_id):
    user_id = get_user_id_from_jwt()

    if user_id is None:
        return redirect(url_for('main.logout'))

    file_record = filesDAO.query_file_by_id(file_id)

    if file_record.user_id != user_id:
        flash('Você não tem permissão para modificar este arquivo.', 'danger')
        return redirect(url_for('main.dashboard'))

    new_name = request.form.get('new_filename', '').strip()

    if not new_name:
        flash('Nome de arquivo inválido.', 'danger')
        return redirect(url_for('main.dashboard'))

    _, ext = os.path.splitext(file_record.original_filename)
    if not new_name.lower().endswith(ext.lower()):
        new_name += ext

    file_record.original_filename = new_name

    new_description = request.form.get('description', '').strip()
    file_record.description = new_description if new_description else None

    db.session.commit()

    flash(f'Arquivo renomeado para "{new_name}" com sucesso!', 'success')
    return redirect(url_for('main.dashboard'))


@bp.route('/delete_file/<int:file_id>', methods=['POST'])
@jwt_required()
def delete_file(file_id):
    user_id = get_user_id_from_jwt()

    if user_id is None:
        return redirect(url_for('main.logout'))
        
    file_record = filesDAO.query_file_by_id(file_id)
    
    if file_record.user_id != user_id:
        flash('Você não tem permissão para excluir este arquivo.', 'danger')
        return redirect(url_for('main.dashboard'))

    try:
        metadata = (
            file_record.image_metadata
            or file_record.video_metadata
            or file_record.audio_metadata
        )
    
        delete_file_from_s3(file_record.stored_filename, metadata)

        filesDAO.delete_file(file_record)
        flash(f'Arquivo "{file_record.original_filename}" excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Ocorreu um erro ao tentar excluir o arquivo.', 'danger')

    return redirect(url_for('main.dashboard'))


@bp.route('/edit_profile', methods=['GET', 'POST'])
@jwt_required()
def edit_profile():

    user_id = get_user_id_from_jwt()

    if user_id is None:
        return redirect(url_for('main.logout'))

    current_user = userDAO.user_by_id(user_id)

    if request.method == 'POST':
        desc = request.form['description']

        current_user.full_name = request.form['full_name']
        current_user.email = request.form['email']
        current_user.description = desc if desc.strip() != "" else None

        if request.form.get('password'):
            current_user.password = generate_password_hash(request.form['password'])

        if 'profile_image' in request.files:
            image = request.files['profile_image']

            if image and image.filename != '':
                from io import BytesIO

                image_bytes = image.read()
                image_file = BytesIO(image_bytes)
                image_file.seek(0)

                file_key = f"users/profile/{user_id}_{image.filename}"

                s3.upload_fileobj(
                    image_file,
                    s3_handle.BUCKET_NAME,
                    file_key,
                    ExtraArgs={'ContentType': image.content_type}
                )

                current_user.profile_image = file_key

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('main.dashboard'))

    def generate_presigned_url(key, expiration=3600):
        return s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': s3_handle.BUCKET_NAME, 'Key': key},
            ExpiresIn=expiration
    )

    profile_url = generate_presigned_url(current_user.profile_image) if current_user.profile_image else None

    return render_template('edit_profile.html', user=current_user, profile_url=profile_url)
