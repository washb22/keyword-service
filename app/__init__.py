# app/__init__.py
from flask import Flask
from flask_migrate import Migrate
from flask_cors import CORS
from config import Config
from .models import db

migrate = Migrate()

def create_app(config_class=Config):
   app = Flask(__name__)
   app.config.from_object(config_class)
   app.config['JSON_AS_ASCII'] = False

   # CORS 설정 수정 - Vercel 도메인 추가
   CORS(app, origins=[
       "http://localhost:5173",
       "https://keyword-frontend.vercel.app",
       "https://keyword-frontend-*.vercel.app"
   ])

   db.init_app(app)
   migrate.init_app(app, db)

   # 인증 블루프린트 등록
   from .auth.routes import auth_bp
   app.register_blueprint(auth_bp, url_prefix='/auth')

   # 키워드 블루프린트 등록
   from .keyword.routes import keyword_bp
   app.register_blueprint(keyword_bp, url_prefix='/keyword')

   @app.route("/")
   def index():
       return "코드 변경 테스트 성공!"

   return app