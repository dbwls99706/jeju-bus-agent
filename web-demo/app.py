"""Isolated synthetic-data web demonstration; not the contest runtime."""
import os
from urllib.parse import urlsplit
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.exceptions import HTTPException
from agent import catalog, prepare_analysis, analyze, prepare_claim_analysis, analyze_claim
from planner import QuestionScopeError
app = Flask(__name__, static_folder=None)
app.config['MAX_CONTENT_LENGTH'] = 16384

@app.before_request
def validate_request():
    hosts = {'localhost', '127.0.0.1'}
    hosts.update(h for h in (os.getenv('VERCEL_URL'), os.getenv('VERCEL_PROJECT_PRODUCTION_URL'), os.getenv('PUBLIC_APP_HOST')) if h)
    if request.host not in hosts and request.host.split(':')[0] not in {'localhost','127.0.0.1'}:
        return jsonify(error='허용된 서비스 주소로 접속하세요.'), 403
    if request.method == 'POST':
        origin = request.headers.get('Origin')
        if origin and origin != request.host_url.rstrip('/'):
            return jsonify(error='다른 사이트의 요청은 허용하지 않습니다.'), 403
        if request.headers.get('Sec-Fetch-Site') == 'cross-site':
            return jsonify(error='다른 사이트의 요청은 허용하지 않습니다.'), 403
        if not request.is_json:
            return jsonify(error='JSON 요청만 허용합니다.'), 415

@app.after_request
def headers(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response

@app.get('/')
def home(): return send_from_directory('static','index.html')

@app.get('/static/<name>')
def static_file(name):
    if name not in {'styles.css','app.js','local-csv.js','local-csv.css','favicon.svg'}:return jsonify(error='찾을 수 없습니다.'),404
    return send_from_directory('static',name)

@app.get('/api/catalog')
def metadata():
    result=catalog()
    result['data_kind']='synthetic'
    result['ai_enabled']=False
    return jsonify(result)

@app.post('/api/<operation>')
def api(operation):
    if operation not in {'plan','analyze','claim-plan','claim-check'}:return jsonify(error='찾을 수 없습니다.'),404
    data=request.get_json()
    if not isinstance(data,dict):return jsonify(error='객체 형식의 JSON이 필요합니다.'),400
    args=(data.get('question'),data.get('start_date'),data.get('end_date'),data.get('user_type','일반'))
    if operation in {'analyze','claim-check'} and not isinstance(data.get('expected_plan'),dict):
        return jsonify(error='분석 계획을 먼저 확인하세요.'),400
    try:
        if operation=='plan':result=prepare_analysis(*args)
        elif operation=='analyze':result=analyze(*args,data['expected_plan'])
        elif operation=='claim-plan':result=prepare_claim_analysis(*args,data.get('claim'))
        else:result=analyze_claim(*args,data.get('claim'),data['expected_plan'])
        result['demo_notice']='합성 데이터·규칙 모드 시연. 실제 데이터나 AI 응답이 아닙니다.'
        # A plan must remain byte-for-byte equivalent to the core plan for approval validation.
        if operation.endswith('plan'):result.pop('demo_notice',None)
        return jsonify(result)
    except (QuestionScopeError,ValueError,TypeError,AttributeError):
        return jsonify(error='질문과 선택 조건을 확인하세요. 합성 자료 범위는 2024년 1~2월입니다.'),400

@app.errorhandler(Exception)
def errors(error):
    if isinstance(error,HTTPException):return jsonify(error='요청을 처리할 수 없습니다.'),error.code
    return jsonify(error='시연 자료를 처리하지 못했습니다.'),500
