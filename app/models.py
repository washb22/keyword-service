# app/models.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    keyword_text = db.Column(db.String(100), nullable=False)
    post_url = db.Column(db.Text, nullable=False)
    ranking_status = db.Column(db.String(50), nullable=True, default='확인 대기')
    last_checked_at = db.Column(db.DateTime, nullable=True)
    priority = db.Column(db.String(10), nullable=False, default='중')
    ranking = db.Column(db.Integer, nullable=True) # <-- 이 줄을 추가하세요
    section = db.Column(db.String(100), nullable=True) # <-- 이 줄만 추가하시면 됩니다.
    post_title = db.Column(db.String(200), nullable=True)  # 새로 추가