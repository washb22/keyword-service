# config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-fallback'
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    
    # PostgreSQL URL 처리 (Render에서 제공하는 postgres:// 를 postgresql:// 로 변환)
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://')
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False