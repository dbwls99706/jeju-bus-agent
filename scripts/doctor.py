"""Read-only installation checks. No downloads, credentials, or external requests."""
import sys,os,json,platform,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.chdir(ROOT)
import agent
checks=[{'item':'Python3.10+','ok':sys.version_info>=(3,10),'detail':platform.python_version()},{'item':'운영체제','ok':True,'detail':platform.system()}]
try:
 meta=agent.catalog();checks.append({'item':'원본 스키마·SHA-256','ok':True,'detail':f"{meta['rows']}행, {meta['min_date']}~{meta['max_date']}"})
except Exception as e:checks.append({'item':'원본 스키마·SHA-256','ok':False,'detail':type(e).__name__+': 원본 CSV 위치 또는 해시를 확인하세요.'})
for module in ('torch','transformers'):
 checks.append({'item':module,'ok':importlib.util.find_spec(module) is not None,'detail':'AI 모드에 필요; 규칙 모드에는 불필요'})
model=Path(os.environ.get('BUS_MODEL_DIR',str(ROOT/'models/qwen15')))
checks.append({'item':'로컬 모델 파일','ok':(model/'config.json').is_file() and any(model.glob('*.safetensors')),'detail':'AI 모드에 필요; 설치 스크립트로 고정 리비전 다운로드'})
print(json.dumps({'checks':checks,'note':'설치 파일 점검이며 Windows UI·모델 추론·센터PC 실측을 대신하지 않습니다.'},ensure_ascii=False,indent=2))
