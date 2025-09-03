# config.py
import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # 아래 SECRET_KEY 라인을 추가하세요.
    SECRET_KEY = 'super-secret-key' # 실제 서비스에서는 더 복잡하고 긴 값으로 변경해야 합니다.
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'site.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False