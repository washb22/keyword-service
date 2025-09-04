# app/auth/routes.py

from flask import Blueprint, request, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db, User
import jwt
from datetime import datetime, timedelta
from functools import wraps
from app.utils import json_response
import os
from google.oauth2 import id_token
from google.auth.transport import requests

auth_bp = Blueprint('auth', __name__)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        if not token:
            return json_response({'message': 'Token is missing!'}, status=401)
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(id=data['user_id']).first()
        except:
            return json_response({'message': 'Token is invalid!'}, status=401)
        return f(current_user, *args, **kwargs)
    return decorated

@auth_bp.route('/profile')
@token_required
def get_profile(current_user):
    return json_response({'email': current_user.email})

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not 'email' in data or not 'password' in data:
        return json_response({'message': 'Missing email or password'}, status=400)
    if User.query.filter_by(email=data['email']).first():
        return json_response({'message': 'User already exists'}, status=409)
    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    new_user = User(email=data['email'], password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return json_response({'message': 'User created successfully!'}, status=201)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not 'email' in data or not 'password' in data:
        return json_response({'message': 'Missing email or password'}, status=400)
    user = User.query.filter_by(email=data['email']).first()
    if not user or not check_password_hash(user.password, data['password']):
        return json_response({'message': 'Could not verify'}, status=401)
    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, current_app.config['SECRET_KEY'], algorithm="HS256")
    return json_response({'token': token})

# 구글 로그인 추가
@auth_bp.route('/google-login', methods=['POST'])
def google_login():
    try:
        data = request.get_json()
        token = data.get('credential')  # Google에서 받은 ID 토큰
        
        # Google ID 토큰 검증
        idinfo = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            os.getenv('GOOGLE_CLIENT_ID')
        )
        
        # 사용자 정보 추출
        email = idinfo['email']
        name = idinfo.get('name', email.split('@')[0])
        
        # 사용자 찾기 또는 생성
        user = User.query.filter_by(email=email).first()
        if not user:
            # 구글 OAuth 사용자는 특별한 비밀번호 설정
            hashed_password = generate_password_hash('google_oauth_' + email, method='pbkdf2:sha256')
            user = User(
                email=email,
                password=hashed_password
            )
            db.session.add(user)
            db.session.commit()
        
        # JWT 토큰 생성
        token = jwt.encode({
            'user_id': user.id,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, current_app.config['SECRET_KEY'], algorithm="HS256")
        
        return json_response({
            'message': 'Google login successful',
            'token': token,
            'email': user.email
        })
        
    except ValueError as e:
        return json_response({'message': 'Invalid Google token'}, status=401)
    except Exception as e:
        return json_response({'message': str(e)}, status=500)