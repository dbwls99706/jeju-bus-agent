import sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
import json,time
from pathlib import Path
from planner import plan
if '--check' in sys.argv:
 print('PASS: project modules import from any working directory (no inference performed)');raise SystemExit(0)
if not os.environ.get('BUS_MODEL_DIR') and (ROOT/'models/qwen15/config.json').exists():os.environ['BUS_MODEL_DIR']=str(ROOT/'models/qwen15')
if not os.environ.get('BUS_MODEL_DIR') or not Path(os.environ['BUS_MODEL_DIR']).is_dir():
 raise SystemExit('로컬 모델이 없습니다. 모델 다운로드 후 BUS_MODEL_DIR를 지정하세요. 기존 평가 기록은 변경하지 않았습니다.')
cases=[('시간 구간마다 평균을 보고 싶습니다','time'),('요일을 월요일부터 순서대로 보여 주세요','weekday'),('한 달씩 묶어서 변화 그래프를 그려 주세요','month'),('청소년과 어린이의 기록량을 비교해 주세요','user_type'),('출퇴근 무렵의 이용 기록을 읽고 싶어요','time'),('월 단위로 묶은 평균이 궁금합니다','month'),('이 자료에서 이용자 구분 간 차이를 보고 싶어요','user_type'),('무슨 요일에 관측된 값이 더 큽니까','weekday')]
results=[]
for q,expected in cases:
 t=time.time();actual,mode,warning=plan(q);r={'question':q,'expected':expected,'actual':actual,'mode':mode,'exact':actual==expected,'seconds':round(time.time()-t,3),'warning':warning};results.append(r);print(json.dumps(r,ensure_ascii=False),flush=True)
Path('research/ai-holdout.json').write_text(json.dumps({'description':'프롬프트와 규칙 수정 후 새로 정한8문항 첫실행. 이후 이 결과로 규칙을 수정하지 않음. 소규모 내부검증이며 외부평가아님.','model':'Qwen2.5-1.5B-Instruct','revision':'989aa7980e4cf806f80c7fef2b1adb7bc71aa306','results':results},ensure_ascii=False,indent=2))
