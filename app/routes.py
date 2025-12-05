from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User, db, File
import os
import uuid 
from werkzeug.utils import secure_filename
from sqlalchemy import or_
from flask_jwt_extended import create_access_token
from flask_jwt_extended import jwt_required
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import set_access_cookies
from flask_jwt_extended import unset_jwt_cookies 

BASEDIR = os.path.abspath(os.path.dirname(__file__))


UPLOAD_FOLDER = os.path.join(BASEDIR, 'static', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

bp = Blueprint('main', __name__)


def save_file(uploaded_file):
    filename = secure_filename(uploaded_file.filename)
    unique_filename = str(uuid.uuid4()) + "_" + filename
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    uploaded_file.save(file_path)
    return unique_filename, uploaded_file.content_type, os.path.getsize(file_path)


def get_user_id_from_jwt():
    user_id_str = get_jwt_identity()
    try:
        # Tenta converter para inteiro, necessário para consultas SQL
        return int(user_id_str)
    except (TypeError, ValueError):
        # Em caso de falha na conversão (token inválido/corrompido)
        return None

@bp.route('/')
def home():
    return redirect(url_for('main.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('User already exists', 'danger')
            return redirect(url_for('main.register'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, full_name=full_name, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html')



@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

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

    current_user = User.query.get_or_404(user_id) 

    # ------------------- Lógica POST -------------------
    if request.method == 'POST':
        if 'file_to_upload' not in request.files or request.files['file_to_upload'].filename == '':
            flash('Nenhum arquivo selecionado.', 'danger')
            return redirect(request.url)

        file = request.files['file_to_upload']

        if file:
            try:
                stored_filename, file_type, file_size = save_file(file)

                new_file = File(
                    original_filename=file.filename,
                    stored_filename=stored_filename,
                    file_type=file_type,
                    file_size=file_size,
                    user_id=user_id 
                )
                db.session.add(new_file)
                db.session.commit()
                flash(f'Arquivo "{file.filename}" carregado com sucesso!', 'success')
            except Exception as e:
                db.session.rollback()
                flash('Ocorreu um erro durante o upload do arquivo.', 'danger')

            return redirect(url_for('main.dashboard'))

    # ------------------- Lógica GET -------------------
    search_query = request.args.get('search', '').strip()
    query = File.query.filter_by(user_id=user_id)
    
    if search_query:
        query = query.filter(or_(
            File.original_filename.ilike(f'%{search_query}%'),
            File.file_type.ilike(f'%{search_query}%')
        ))
        
    user_files = query.order_by(File.upload_date.desc()).all()
    

    return render_template('dashboard.html', user=current_user, files=user_files, search_query=search_query)



@bp.route('/view_file/<int:file_id>')
@jwt_required()
def view_file(file_id):
    user_id = get_user_id_from_jwt()
    if user_id is None:
        return redirect(url_for('main.logout'))

    file_record = File.query.get_or_404(file_id)
    
    if file_record.user_id != user_id: 
        flash('Você não tem permissão para visualizar este arquivo.', 'danger')
        return redirect(url_for('main.dashboard'))

    return render_template('view_media.html', file=file_record, user=User.query.get(user_id))


@bp.route('/download/<int:file_id>')
@jwt_required()
def download_file(file_id):
    user_id = get_user_id_from_jwt()
    if user_id is None:
        return redirect(url_for('main.logout'))

    file_record = File.query.get_or_404(file_id)
    
    if file_record.user_id != user_id:
        flash('Você não tem permissão para acessar este arquivo.', 'danger')
        return redirect(url_for('main.dashboard'))

    return send_from_directory(
        UPLOAD_FOLDER,
        file_record.stored_filename,
        as_attachment=True,
        download_name=file_record.original_filename
    )



@bp.route('/rename_file/<int:file_id>', methods=['POST'])
@jwt_required()
def rename_file(file_id):
    user_id = get_user_id_from_jwt()
    if user_id is None:
        return redirect(url_for('main.logout'))

    file_record = File.query.get_or_404(file_id)
    
    if file_record.user_id != user_id:
        flash('Você não tem permissão para modificar este arquivo.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    new_name = request.form.get('new_filename', '').strip()
    if new_name:
        _, ext = os.path.splitext(file_record.original_filename)
        if not new_name.lower().endswith(ext.lower()):
            new_name += ext
            
        file_record.original_filename = new_name
        db.session.commit()
        flash(f'Arquivo renomeado para "{new_name}" com sucesso!', 'success')
    else:
        flash('Nome de arquivo inválido.', 'danger')

    return redirect(url_for('main.dashboard'))



@bp.route('/delete_file/<int:file_id>', methods=['POST'])
@jwt_required()
def delete_file(file_id):
    user_id = get_user_id_from_jwt()
    if user_id is None:
        return redirect(url_for('main.logout'))
        
    file_record = File.query.get_or_404(file_id)
    
    if file_record.user_id != user_id:
        flash('Você não tem permissão para excluir este arquivo.', 'danger')
        return redirect(url_for('main.dashboard'))

    try:
        file_path = os.path.join(UPLOAD_FOLDER, file_record.stored_filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        db.session.delete(file_record)
        db.session.commit()
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
        
    current_user = User.query.get_or_404(user_id) 
    
    if request.method == 'POST':
        desc = request.form['description']

        current_user.full_name = request.form['full_name']
        current_user.email = request.form['email']
        current_user.description = desc if desc.strip() != "" else None

        if request.form.get('password'):
            current_user.password = generate_password_hash(request.form['password'])

        if 'profile_image' in request.files:
            image = request.files['profile_image']
            if image.filename != '':
                image.save(os.path.join('app/static/profile_pics', image.filename))
                current_user.profile_image = image.filename

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('main.dashboard'))
        
    return render_template('edit_profile.html', user=current_user)
