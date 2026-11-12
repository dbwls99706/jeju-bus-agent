import sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
import json,time,os
from pathlib import Path
from planner import local_plan,plan
if '--check' in sys.argv:
 print('PASS: project modules import from any working directory (no inference performed)');raise SystemExit(0)
if not os.environ.get('BUS_MODEL_DIR') and (ROOT/'models/qwen15/config.json').exists():os.environ['BUS_MODEL_DIR']=str(ROOT/'models/qwen15')
if not os.environ.get('BUS_MODEL_DIR') or not Path(os.environ['BUS_MODEL_DIR']).is_dir():
 raise SystemExit('로컬 모델이 없습니다. 모델 다운로드 후 BUS_MODEL_DIR를 지정하세요. 기존 평가 기록은 변경하지 않았습니다.')
CASES=[('어느 시간대에 많이 타나요?','time'),('평일과 주말을 비교해줘','weekday'),('월별 추이를 보여줘','month'),('이용자 유형을 비교해줘','user_type'),('아침과 저녁의 기록이 궁금해','time'),('토요일과 일요일을 보고 싶어','weekday'),('매달 승차 기록이 어떻게 달라졌어?','month'),('경로와 일반은 어떻게 달라?','user_type'),('하루 중 언제 이용이 많았나요?','time'),('일주일 중 어느 날의 기록이 높아?','weekday'),('연중 변화 추세를 알려줘','month'),('나이대마다 차이가 있어?','user_type')]
results=[]
for q,expected in CASES:
 t=time.time()
 try: actual=local_plan(q);error=None
 except Exception as e:actual=None;error=str(e)
 r={'question':q,'expected':expected,'actual':actual,'exact':actual==expected,'seconds':round(time.time()-t,3),'error':error};results.append(r);print(json.dumps(r,ensure_ascii=False),flush=True)
Path('research/ai-evaluation.json').write_text(json.dumps({'model':'Qwen2.5-1.5B-Instruct','revision':'989aa7980e4cf806f80c7fef2b1adb7bc71aa306','dtype':'bfloat16','device':'CPU','results':results},ensure_ascii=False,indent=2))
