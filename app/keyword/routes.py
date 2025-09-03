# app/keyword/routes.py

# jsonify를 지우고, 우리가 만든 json_response를 가져옵니다.
from flask import Blueprint, request
from app.models import db, Keyword
from app.auth.routes import token_required
from .scraper import run_check
from datetime import datetime
from app.utils import json_response # <-- 이 줄 추가

keyword_bp = Blueprint('keyword', __name__)


@keyword_bp.route('/keywords', methods=['POST'])
@token_required
def create_keyword(current_user):
    data = request.get_json()
    if not data or not 'keyword_text' in data or not 'post_url' in data:
        return json_response({'message': 'Required fields are missing!'}, status=400) # jsonify -> json_response
    new_keyword = Keyword(
        user_id=current_user.id,
        keyword_text=data['keyword_text'],
        post_url=data['post_url'],
        priority=data.get('priority', '중')
    )
    db.session.add(new_keyword)
    db.session.commit()
    return json_response({'message': 'New keyword created!'}, status=201) # jsonify -> json_response


@keyword_bp.route('/keywords', methods=['GET'])
@token_required
def get_keywords(current_user):
    keywords = Keyword.query.filter_by(user_id=current_user.id).all()
    output = []
    for keyword in keywords:
        keyword_data = {
            'id': keyword.id,
            'keyword_text': keyword.keyword_text,
            'post_url': keyword.post_url,
            'priority': keyword.priority,
            'ranking_status': keyword.ranking_status,
            'last_checked_at': keyword.last_checked_at.isoformat() if keyword.last_checked_at else None
        }
        output.append(keyword_data)
    return json_response({'keywords': output}) # jsonify -> json_response


@keyword_bp.route('/keywords/<int:keyword_id>/check', methods=['POST'])
@token_required
def check_keyword_ranking(current_user, keyword_id):
    keyword = Keyword.query.filter_by(id=keyword_id, user_id=current_user.id).first()
    if not keyword:
        return json_response({'message': 'Keyword not found or permission denied'}, status=404) # jsonify -> json_response
    try:
        status = run_check(keyword.keyword_text, keyword.post_url)
        keyword.ranking_status = status
        keyword.last_checked_at = datetime.utcnow()
        db.session.commit()
        return json_response({'message': f'Check complete. Status: {status}'}) # jsonify -> json_response
    except Exception as e:
        return json_response({'message': f'An error occurred: {str(e)}'}, status=500) # jsonify -> json_response