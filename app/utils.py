# app/utils.py
import json
from flask import Response

def json_response(data, status=200):
    """
    한글이 깨지지 않는 커스텀 JSON 응답 함수
    """
    return Response(
        json.dumps(data, ensure_ascii=False),
        status=status,
        mimetype='application/json; charset=utf-8'
    )