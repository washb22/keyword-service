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


# app/keyword/routes.py의 check_keyword_ranking 함수
@keyword_bp.route('/keywords/<int:keyword_id>/check', methods=['POST'])
@token_required
def check_keyword_ranking(current_user, keyword_id):
    keyword = Keyword.query.filter_by(id=keyword_id, user_id=current_user.id).first()
    if not keyword:
        return json_response({'message': 'Keyword not found or permission denied'}, status=404)
    try:
        # 봇으로부터 (상태, 순위) 두 값을 받음
        status, rank = run_check(keyword.keyword_text, keyword.post_url)
        
        # 두 값 모두 DB에 업데이트
        keyword.ranking_status = status
        keyword.ranking = rank
        keyword.last_checked_at = datetime.utcnow()
        db.session.commit()
        
        # 응답 메시지도 순위를 포함하도록 변경
        response_message = f'Check complete. Status: {status}'
        if rank:
            response_message += f', Rank: {rank}'
        return json_response({'message': response_message})
    except Exception as e:
        traceback.print_exc() 
        return json_response({'message': f'An error occurred: {str(e)}'}, status=500)