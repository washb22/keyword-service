# app/keyword/routes.py

# jsonify를 지우고, 우리가 만든 json_response를 가져옵니다.
from flask import Blueprint, request
from app.models import db, Keyword
from app.auth.routes import token_required
from .scraper import run_check
from datetime import datetime
from app.utils import json_response
from datetime import datetime, timezone # timezone 추가
import traceback  # <-- 이 줄 추가

keyword_bp = Blueprint('keyword', __name__)


@keyword_bp.route('/keywords', methods=['POST'])
@token_required
def create_keyword(current_user):
    data = request.get_json()
    if not data or not 'keyword_text' in data or not 'post_url' in data:
        return json_response({'message': 'Required fields are missing!'}, status=400)
    new_keyword = Keyword(
        user_id=current_user.id,
        keyword_text=data['keyword_text'],
        post_url=data['post_url'],
        post_title=data.get('post_title'),  # 이 줄이 있는지 확인!
        priority=data.get('priority', '중')
    )
    db.session.add(new_keyword)
    db.session.commit()
    return json_response({'message': 'New keyword created!'}, status=201)


@keyword_bp.route('/keywords', methods=['GET'])
@token_required
def get_keywords(current_user):
    keywords = Keyword.query.filter_by(user_id=current_user.id).order_by(Keyword.id.desc()).all()
    output = []
    for keyword in keywords:
        keyword_data = {
            'id': keyword.id,
            'keyword_text': keyword.keyword_text,
            'post_url': keyword.post_url,
            'post_title': keyword.post_title,  # 이 줄이 있는지 확인!
            'priority': keyword.priority,
            'ranking_status': keyword.ranking_status,
            'ranking': keyword.ranking,
            'section': keyword.section,
            'last_checked_at': keyword.last_checked_at.isoformat() if keyword.last_checked_at else None
        }
        output.append(keyword_data)
    return json_response({'keywords': output})


@keyword_bp.route('/keywords/<int:keyword_id>/check', methods=['POST'])
@token_required
def check_keyword_ranking(current_user, keyword_id):
    keyword = Keyword.query.filter_by(id=keyword_id, user_id=current_user.id).first()
    if not keyword:
        return json_response({'message': 'Keyword not found or permission denied'}, status=404)
    
    try:
        print(f"키워드 '{keyword.keyword_text}' 순위 확인 시작...")
        
        # 봇으로부터 (상태, 순위, 섹션제목) 세 값을 받음
        status, rank, section = run_check(keyword.keyword_text, keyword.post_url, keyword.post_title)
        
        print(f"스크래핑 결과 - 상태: {status}, 순위: {rank}, 섹션: {section}")
        
        # 세 값 모두 DB에 업데이트
        keyword.ranking_status = status
        keyword.ranking = rank
        keyword.section = section
        keyword.last_checked_at = datetime.now(timezone.utc) # UTC 시간임을 명시
        
        db.session.commit()
        print("DB 업데이트 완료")
        
        # 응답 메시지 구성
        if rank and rank > 0:
            response_message = f'순위 확인 완료. {section} 섹션에서 {rank}위에 노출되고 있습니다.'
        elif status == "노출X":
            response_message = f'순위 확인 완료. 현재 노출되지 않고 있습니다.'
        else:
            response_message = f'순위 확인 완료. 상태: {status}'

        return json_response({
            'message': response_message,
            'status': status,
            'ranking': rank,
            'section': section
        })
        
    except Exception as e:
        print(f"순위 확인 중 오류 발생: {str(e)}")
        traceback.print_exc()
        return json_response({'message': f'순위 확인 중 오류가 발생했습니다: {str(e)}'}, status=500)


@keyword_bp.route('/keywords/<int:keyword_id>', methods=['PUT'])
@token_required
def update_keyword(current_user, keyword_id):
    """키워드 수정 API"""
    keyword = Keyword.query.filter_by(id=keyword_id, user_id=current_user.id).first()
    if not keyword:
        return json_response({'message': 'Keyword not found or permission denied'}, status=404)

    data = request.get_json()
    if not data:
        return json_response({'message': 'Request body is missing!'}, status=400)

    # 수정 가능한 필드들 업데이트
    keyword.keyword_text = data.get('keyword_text', keyword.keyword_text)
    keyword.post_title = data.get('post_title', keyword.post_title)  # 이 줄 추가
    keyword.post_url = data.get('post_url', keyword.post_url)
    keyword.priority = data.get('priority', keyword.priority)

    db.session.commit()

    # 수정된 키워드 정보 반환
    updated_keyword_data = {
        'id': keyword.id,
        'keyword_text': keyword.keyword_text,
        'post_url': keyword.post_url,
        'priority': keyword.priority,
    }
    return json_response({'message': 'Keyword updated successfully!', 'keyword': updated_keyword_data})


@keyword_bp.route('/keywords/<int:keyword_id>', methods=['DELETE'])
@token_required
def delete_keyword(current_user, keyword_id):
    """키워드 삭제 API"""
    keyword = Keyword.query.filter_by(id=keyword_id, user_id=current_user.id).first()
    if not keyword:
        return json_response({'message': 'Keyword not found or permission denied'}, status=404)

    db.session.delete(keyword)
    db.session.commit()

    return json_response({'message': f'Keyword with ID {keyword_id} has been deleted.'})