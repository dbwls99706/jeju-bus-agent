"""Local launcher with preflight checks and browser handoff. No upload/install."""
import os,sys,threading,webbrowser,importlib.util,json,time
from urllib.request import build_opener,ProxyHandler
# Loopback readiness checks must never travel through an environment proxy.
urlopen=build_opener(ProxyHandler({})).open
from pathlib import Path
from http.server import ThreadingHTTPServer
ROOT=Path(__file__).resolve().parent

def create_server(handler,port=None):
    explicit=port is not None
    try:first=int(port) if explicit else 8765
    except (TypeError,ValueError):raise ValueError('PORT는 0~65535 사이 정수여야 합니다.') from None
    if not 0<=first<=65535:raise ValueError('PORT는 0~65535 사이 정수여야 합니다.')
    for candidate in ([first] if explicit else range(first,first+10)):
        try:return ThreadingHTTPServer(('127.0.0.1',candidate),handler)
        except OSError as exc:
            if explicit:raise OSError(f'지정 포트 {first}를 열 수 없습니다. 실행 중인 앱을 확인하거나 PORT를 바꾸세요.') from exc
    raise OSError('8765~8774 포트를 열 수 없습니다. 다른 프로그램을 종료하거나 PORT를 지정하세요.')

def open_browser(url,expected_sha):
    # Open only after our bound server answers with the verified dataset.
    ready=False
    for attempt in range(20):
        try:
            with urlopen(url+'/api/catalog',timeout=.2) as response:payload=json.load(response)
            if payload.get('sha256')==expected_sha:ready=True;break
        except Exception:pass
        time.sleep(.1)
    if not ready:
        print('준비 상태를 확인하지 못해 브라우저를 열지 않았습니다. 위 주소와 서버 메시지를 확인하세요.',flush=True);return
    try:
        if not webbrowser.open(url,new=2):print('브라우저를 자동으로 열지 못했습니다. 위 주소를 브라우저에 붙여 넣으세요.',flush=True)
    except Exception:print('브라우저를 자동으로 열지 못했습니다. 위 주소를 브라우저에 붙여 넣으세요.',flush=True)

def prepare_environment():
    # Resolve user-supplied relative paths before changing the working directory.
    for key in ('BUS_DATA_PATH','BUS_MODEL_DIR'):
        if os.environ.get(key):os.environ[key]=str(Path(os.environ[key]).expanduser().resolve())
    os.chdir(ROOT)
    if not os.environ.get('BUS_DATA_PATH') and not (ROOT/'data/bus.csv').is_file():
        try:
            import tkinter as tk
            from tkinter.filedialog import askopenfilename
            root=tk.Tk();root.withdraw()
            try:path=askopenfilename(title='일별시간대별버스승차인원수현황.csv 선택',filetypes=[('CSV','*.csv')])
            finally:root.destroy()
        except Exception:raise ValueError('원본 CSV를 찾을 수 없습니다. data/bus.csv에 넣거나 BUS_DATA_PATH에 파일 경로를 지정하세요.') from None
        if not path:raise ValueError('파일 선택을 취소했습니다. 다시 실행하면 선택할 수 있습니다.')
        os.environ['BUS_DATA_PATH']=path
    if os.environ.get('BUS_MODEL_DIR'):
        model=Path(os.environ['BUS_MODEL_DIR'])
        if not (model/'config.json').is_file() or not any(model.glob('*.safetensors')):
            raise ValueError('AI 모델이 없습니다. README의 설치 단계에서 python scripts/download_model.py를 실행하세요.')
        if any(importlib.util.find_spec(m) is None for m in ('torch','transformers')):
            raise ValueError('AI 패키지가 없습니다. README의 가상환경 설치 단계를 완료하거나 start.bat로 규칙 모드를 실행하세요.')
    import agent
    try:meta=agent.catalog()
    except Exception:raise ValueError('원본 CSV 위치·내용이 확인된 자료와 다릅니다. python scripts/doctor.py로 확인하세요. 임의 파일은 분석하지 않았습니다.') from None
    return meta

def main():
    if sys.version_info<(3,10):print('Python 3.10 이상이 필요합니다. 권장 버전은 3.12입니다.',flush=True);return 1
    server=None
    try:
        meta=prepare_environment()
        from server import Handler
        server=create_server(Handler,os.environ.get('PORT'))
        url=f'http://127.0.0.1:{server.server_port}'
        print(f'원본 확인 완료: {meta["rows"]:,}개 기록. 외부로 업로드하지 않습니다.',flush=True)
        print('실행 모드: '+('로컬 AI(첫 질문 시 모델 로딩)' if os.environ.get('BUS_MODEL_DIR') else '규칙 기반'),flush=True)
        print('제주 버스 데이터 길잡이: '+url,flush=True)
        print('이 창을 유지하세요. 종료: Ctrl+C. 브라우저가 안 열리면 위 주소로 접속하세요.',flush=True)
        if os.environ.get('BUS_OPEN_BROWSER','1')!='0':
            timer=threading.Timer(.3,open_browser,args=(url,meta['sha256']));timer.daemon=True;timer.start()
        server.serve_forever()
    except KeyboardInterrupt:print('\n분석 서버를 종료했습니다.',flush=True)
    except (ValueError,OSError) as exc:print('실행하지 못했습니다: '+str(exc),flush=True);return 1
    finally:
        if server:server.server_close()
    return 0

if __name__=='__main__':raise SystemExit(main())
