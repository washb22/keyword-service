# config.py
import os

class Config:
    SECRET_KEY = 'super-secret-key'  # 실제 서비스에서는 더 복잡하고 긴 값으로 변경해야 합니다.
    SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False