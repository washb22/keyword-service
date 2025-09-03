# app/auth/routes.py

# jsonify를 지우고, current_app을 추가하고, 우리가 만든 json_response를 가져옵니다.
from flask import Blueprint, request, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db, User
import jwt
from datetime import datetime, timedelta
from functools import wraps
from app.utils import json_response # <-- 이 줄 추가

auth_bp = Blueprint('auth', __name__)

# (token_required 데코레이터 코드는 변경 없음)
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        if not token:
            return json_response({'message': 'Token is missing!'}, status=401) # jsonify -> json_response
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(id=data['user_id']).first()
        except:
            return json_response({'message': 'Token is invalid!'}, status=401) # jsonify -> json_response
        return f(current_user, *args, **kwargs)
    return decorated


@auth_bp.route('/profile')
@token_required
def get_profile(current_user):
    return json_response({'email': current_user.email}) # jsonify -> json_response


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not 'email' in data or not 'password' in data:
        return json_response({'message': 'Missing email or password'}, status=400) # jsonify -> json_response
    if User.query.filter_by(email=data['email']).first():
        return json_response({'message': 'User already exists'}, status=409) # jsonify -> json_response
    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    new_user = User(email=data['email'], password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return json_response({'message': 'User created successfully!'}, status=201) # jsonify -> json_response


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not 'email' in data or not 'password' in data:
        return json_response({'message': 'Missing email or password'}, status=400) # jsonify -> json_response
    user = User.query.filter_by(email=data['email']).first()
    if not user or not check_password_hash(user.password, data['password']):
        return json_response({'message': 'Could not verify'}, status=401) # jsonify -> json_response
    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, current_app.config['SECRET_KEY'], algorithm="HS256")
    return json_response({'token': token}) # jsonify -> json_response