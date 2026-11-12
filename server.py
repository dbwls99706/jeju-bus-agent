import json, os
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit
from agent import analyze, catalog, prepare_analysis, prepare_claim_analysis, analyze_claim
from planner import QuestionScopeError
BASE=Path(__file__).resolve().parent
class Handler(BaseHTTPRequestHandler):
    def send(self,status,data,kind='application/json; charset=utf-8'):
        body=data if isinstance(data,bytes) else json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)))
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
    def valid_host(self):
        return self.headers.get('Host','') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')
    def do_GET(self):
        if not self.valid_host():return self.send(403,{'error':'로컬 주소로 접속하세요.'})
        path=urlsplit(self.path).path
        try:
            if path=='/api/catalog': return self.send(200,catalog())
            name={'/':'index.html','/index.html':'index.html','/static/styles.css':'styles.css','/static/app.js':'app.js'}.get(path)
            if not name:return self.send(404,{'error':'찾을 수 없습니다.'})
            kinds={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8'}
            p=BASE/'static'/name;return self.send(200,p.read_bytes(),kinds[p.suffix])
        except Exception:return self.send(500,{'error':'자료를 읽지 못했습니다. 설치 상태와 데이터 해시를 확인하세요.'})
    def do_POST(self):
        if not self.valid_host():return self.send(403,{'error':'로컬 주소로 접속하세요.'})
        if self.path not in ('/api/analyze','/api/plan','/api/claim-plan','/api/claim-check'):return self.send(404,{'error':'찾을 수 없습니다.'})
        origin=self.headers.get('Origin','')
        if origin and origin!=f'http://{self.headers.get("Host","")}':return self.send(403,{'error':'다른 사이트 요청은 허용하지 않습니다.'})
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=16384:return self.send(413,{'error':'요청 크기 제한'})
            data=json.loads(self.rfile.read(n))
            if self.path=='/api/claim-plan':return self.send(200,prepare_claim_analysis(data.get('question'),data.get('start_date'),data.get('end_date'),data.get('user_type','일반'),data.get('claim')))
            if self.path=='/api/claim-check':return self.send(200,analyze_claim(data.get('question'),data.get('start_date'),data.get('end_date'),data.get('user_type','일반'),data.get('claim'),data.get('expected_plan')))
            if self.path=='/api/plan':return self.send(200,prepare_analysis(data.get('question'),data.get('start_date'),data.get('end_date'),data.get('user_type','일반')))
            return self.send(200,analyze(data.get('question'),data.get('start_date'),data.get('end_date'),data.get('user_type','일반'),data.get('expected_plan')))
        except QuestionScopeError as e:return self.send(400,{'error':str(e)})
        except (ValueError,TypeError,AttributeError):return self.send(400,{'error':'질문과 데이터 선택을 확인하세요.'})
        except Exception:return self.send(500,{'error':'분석 중 오류. 자료 상태를 확인하세요.'})
if __name__=='__main__':
    port=int(os.environ.get('PORT','8765'))
    print(f'버스여울: http://127.0.0.1:{port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
