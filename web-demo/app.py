"""Public aggregate-data web app with optional quota-guarded AI classification."""
import os
import re
from datetime import date
from openai_planner import classify_question, validate_question, PlannerUnavailable, MODEL
from quota import RedisQuota, QuotaUnavailable
from urllib.parse import urlsplit
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.exceptions import HTTPException
from agent import catalog, prepare_analysis, analyze, prepare_claim_analysis, analyze_claim
from planner import QuestionScopeError
from data_source import get_mode, get_metadata
from pathlib import Path
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
def home():
    html=(Path(__file__).parent/'static/index.html').read_text()
    real = get_mode() == 'real'
    ready = ai_ready()
    title = '실제 제주 버스 승차 집계' if real else '실제 데이터·AI 없는 절차 시연'
    mode = 'AI 분류 선택 가능' if ready else '현재 AI 미사용'
    notice = ('과거 집계 37,057행 · 실시간 정보 아님' if real else '합성 예제로 분석 절차만 체험합니다.')
    detail = ('숫자는 검증된 계산식으로 집계합니다. 출처·이용조건은 아래 자료 상세에서 확인하세요.' if real else '실제 제주 승차 기록이나 AI 응답이 아닙니다.')
    old_start = html.index('<div class="mode-notice"')
    old_end = html.index('</div>', old_start) + len('</div>')
    html = html[:old_start] + f'<div class="mode-notice" role="note"><strong>{notice}</strong><details><summary>자료와 분석 방식</summary><p>{title} · {mode}. {detail}</p></details></div>' + html[old_end:]
    html = html.replace('합성 예제 · AI 미사용', ('실제 집계' if real else '합성 예제') + ' · ' + mode)
    return html


@app.get('/static/<name>')
def static_file(name):
    if name not in {'styles.css','app.js','favicon.svg','social-preview.png','stone-park-01.jpg'}:return jsonify(error='찾을 수 없습니다.'),404
    return send_from_directory('static',name)

@app.get('/api/catalog')
def metadata():
    result=catalog()
    result['data_kind']=get_mode()
    result['ai_enabled']=ai_ready()
    result['ai_role']='질문의 분석 종류만 분류; 숫자 계산은 Python 규칙'
    result['ai_model']=MODEL if result['ai_enabled'] else None
    return jsonify(result)


def ai_ready():
    if os.environ.get('AI_ENABLED') != '1' or not os.environ.get('OPENAI_API_KEY', '').strip():
        return False
    try:
        RedisQuota.from_env()
        return True
    except (ValueError, TypeError):
        return False


def canonical_ai_request(data, dimension):
    axes={'time':'시간대별','weekday':'요일별','month':'월별','user_type':'유형별'}
    metrics={'total':'합계','daily':'일평균','hourly':'시간당 일평균'}
    start,end,user_type,metric=(data.get(k) for k in ('start_date','end_date','user_type','metric'))
    if dimension not in axes or metric not in metrics:
        raise ValueError('Invalid choice')
    if metric == 'hourly' and dimension != 'time':
        raise ValueError('시간당 평균은 시간대 비교에서만 사용할 수 있습니다. 일평균 또는 합계를 선택하세요.')
    for value in (start,end):
        if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):
            raise ValueError('날짜를 선택하세요.')
        date.fromisoformat(value)
    meta=catalog()
    if not isinstance(user_type,str) or user_type not in meta['user_types']+['전체']:
        raise ValueError('유형을 선택하세요.')
    if not meta['min_date'] <= start <= end <= meta['max_date']:
        raise ValueError('자료 범위 안의 날짜를 선택하세요.')
    population='전체 이용자' if user_type=='전체' else user_type
    return {'question':f'{start}~{end} {population} {axes[dimension]} {metrics[metric]} 분석',
            'start_date':start,'end_date':end,'user_type':user_type}


@app.post('/api/ai-plan')
def ai_plan():
    data=request.get_json()
    if not isinstance(data,dict) or data.get('scope_ack') is not True:
        return jsonify(error='AI는 분석 종류만 분류하며 날짜·유형·계산방식은 화면 선택만 적용한다는 안내에 동의해 주세요.'),400
    try:
        question=validate_question(data.get('question'))
        # Validate filters and calculation BEFORE any paid classification.
        initial=canonical_ai_request(data,'time')
        prepare_analysis(**initial)
    except (ValueError,TypeError,KeyError):
        return jsonify(error='질문은 300자 이내로 입력하고 자료 범위 안의 날짜·유형·계산방식을 선택해 주세요.'),400
    if not ai_ready():
        return jsonify(error='AI가 활성화되지 않았습니다. 기존 조건 선택 분석을 이용해 주세요.'),503
    try:
        usage={}
        dimension=classify_question(question,reserve_call=RedisQuota.from_env().reserve_call,usage_callback=usage.update)
        if dimension=='reject':
            return jsonify(error='AI가 지원하는 분석 종류로 분류하지 못했습니다. 조건 선택 분석을 이용해 주세요.',ai_executed=True),422
        original=canonical_ai_request(data,dimension)
        plan=prepare_analysis(**original)
        return jsonify(plan=plan,canonical_request=original,ai_executed=True,ai_model=MODEL,
                       ai_dimension=dimension,ai_usage=usage,ai_scope='분석 종류만 AI 분류. 날짜·유형·계산방식은 화면 선택만 적용. 계산은 Python 규칙.')
    except (PlannerUnavailable,QuotaUnavailable):
        return jsonify(error='AI 호출이 허용되지 않거나 응답을 사용할 수 없습니다. 자동 재시도하지 않았습니다. 조건 선택 분석은 계속 사용할 수 있습니다.'),503
    except (ValueError,TypeError,KeyError):
        return jsonify(error='AI가 고른 분석 종류에 현재 계산방식을 적용할 수 없습니다. 시간당 평균 대신 일평균·합계를 선택하거나 조건 선택 분석을 이용해 주세요.',ai_executed=True),422

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
        result['demo_notice']=get_metadata()['data_notice']+' 숫자 계산은 Python 규칙 기반입니다.'
        # A plan must remain byte-for-byte equivalent to the core plan for approval validation.
        if operation.endswith('plan'):result.pop('demo_notice',None)
        return jsonify(result)
    except (QuestionScopeError,ValueError,TypeError,AttributeError):
        return jsonify(error='질문과 선택 조건을 확인하세요. 자료 범위는 화면의 자료 정보를 확인하세요.'),400

@app.errorhandler(Exception)
def errors(error):
    if isinstance(error,HTTPException):return jsonify(error='요청을 처리할 수 없습니다.'),error.code
    return jsonify(error='시연 자료를 처리하지 못했습니다.'),500
