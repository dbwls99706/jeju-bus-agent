"""Download the pinned model into this project, regardless of shell cwd."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MODEL_ID='Qwen/Qwen2.5-1.5B-Instruct'
REVISION='989aa7980e4cf806f80c7fef2b1adb7bc71aa306'
def main():
    from huggingface_hub import snapshot_download
    destination=ROOT/'models/qwen15'
    snapshot_download(MODEL_ID,revision=REVISION,local_dir=str(destination),allow_patterns=['*.json','*.safetensors','*.txt','*.jinja','LICENSE*','README.md'])
    print('모델 준비 완료: '+str(destination))
    print('Windows: start-ai.bat / 다른 OS: BUS_MODEL_DIR을 위 경로로 지정해 launch.py 실행')
if __name__=='__main__':main()
