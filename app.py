from flask import Flask, render_template, request, jsonify
import requests
import os
from dotenv import load_dotenv
import re
from urllib.parse import unquote

load_dotenv()

app = Flask(__name__)

# 네이버 API 설정
NAVER_CLIENT_ID = os.getenv('NAVER_CLIENT_ID')
NAVER_CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET')
NAVER_API_URL = "https://openapi.naver.com/v1/search/shop.json"

def clean_html_tags(text):
    """HTML 태그 제거"""
    if not text:
        return text
    return re.sub(r'<[^>]+>', '', text)

def format_price(price_str):
    """가격을 정수로 변환"""
    try:
        return int(price_str) if price_str else 0
    except:
        return 0

def process_item(item):
    """API 응답 아이템을 정제"""
    return {
        'title': clean_html_tags(item.get('title', '')),
        'lprice': format_price(item.get('lprice', '0')),
        'hprice': format_price(item.get('hprice', '0')),
        'link': item.get('link', ''),
        'image': item.get('image', ''),
        'productId': item.get('productId', ''),
        'brand': item.get('brand', ''),
        'category': item.get('category', ''),
        'mallName': item.get('mallName', '')
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def search_products():
    """
    상품 검색 API
    요청: { "query": "검색어", "display": 5 }
    응답: { 
        "success": true, 
        "items": [...],
        "lowestPrice": {...},
        "priceRange": {"min": 0, "max": 0}
    }
    """
    try:
        data = request.json
        query = data.get('query', '').strip()
        display = data.get('display', 10)
        
        # 입력값 검증
        if not query:
            return jsonify({
                'success': False, 
                'error': '검색어를 입력하세요'
            }), 400
        
        if len(query) > 100:
            return jsonify({
                'success': False,
                'error': '검색어는 100자 이내여야 합니다'
            }), 400
        
        if display > 100:
            display = 100
        
        # 네이버 API 호출
        headers = {
            'X-Naver-Client-Id': NAVER_CLIENT_ID,
            'X-Naver-Client-Secret': NAVER_CLIENT_SECRET
        }
        params = {
            'query': query,
            'display': min(display, 100),
            'sort': 'asc'  # 가격 오름차순
        }
        
        response = requests.get(NAVER_API_URL, headers=headers, params=params, timeout=10)
        
        if response.status_code != 200:
            return jsonify({
                'success': False, 
                'error': f'API 호출 실패: {response.status_code}'
            }), 400
        
        api_data = response.json()
        items = api_data.get('items', [])
        
        if not items:
            return jsonify({
                'success': False, 
                'error': '검색 결과가 없습니다'
            }), 404
        
        # 아이템 정제
        processed_items = [process_item(item) for item in items]
        
        # 최저가 상품 찾기
        lowest_price_item = min(processed_items, key=lambda x: x['lprice'])
        
        # 가격 범위 계산
        prices = [item['lprice'] for item in processed_items if item['lprice'] > 0]
        price_range = {
            'min': min(prices) if prices else 0,
            'max': max(prices) if prices else 0
        }
        
        # 응답 데이터
        result = {
            'success': True,
            'query': query,
            'total': api_data.get('total', 0),
            'items': processed_items[:display],
            'lowestPrice': lowest_price_item,
            'priceRange': price_range
        }
        
        return jsonify(result), 200
        
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False, 
            'error': '요청 시간 초과. 다시 시도해주세요'
        }), 504
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'오류 발생: {str(e)}'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """헬스 체크 (배포 상태 확인용)"""
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
