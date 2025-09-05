# config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-fallback'
    
    # DATABASE_URL 환경변수 가져오기
    database_url = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    
    # PostgreSQL URL 처리 (Render에서 제공하는 postgres:// 를 postgresql:// 로 변환)
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False