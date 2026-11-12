# 버스여울 웹 체험판

**실제 제주 버스 승차 집계 37,057행 · 기본 규칙 모드 + 선택형 Luna 분석종류 분류.**

제출용 로컬 프로그램과 별도 디렉터리에 구성한 Vercel 웹 앱입니다. 실제 과거 승차 집계의 출처·이용조건 근거 및 한계는 [데이터 안내](data/README.md)에 기록했습니다. 기본 모드는 실제 자료이며 합성 840행은 명시적 테스트 모드에서만 사용됩니다. 모델 가중치·키는 포함하지 않습니다.

## 로컬 실행

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/flask --app app run --host 127.0.0.1 --port 8877
.venv/bin/python -m unittest discover -s tests -v
```

## 배포 후보

Flask WSGI 진입점 `app.py`와 Python 3.12를 사용합니다. Vercel의 기본 `VERCEL_URL`, `VERCEL_PROJECT_PRODUCTION_URL` 호스트를 허용하며 별도 도메인은 `PUBLIC_APP_HOST`로 명시합니다. 원본 제출용 서버와 달리 공개 HTTP 실행에 필요한 진입점을 제공합니다.

Vercel 프로젝트의 Root Directory를 `web-demo`로 설정합니다. 제출용 프로그램은 저장소 루트에 있으며 이 체험판과 별개입니다.

## 제한

- 별도 AI 버튼만 gpt-6-luna를 호출합니다. 질문만 OpenAI에 전송하고 숫자 계산은 Python이 수행합니다. [설정 및 비용 제한](AI_SETUP.md)
- 지정된 실제 CSV의 압축을 풀고 원본 해시를 고정 검사합니다. 불일치 시 실행을 중단합니다.
- 16KB 요청 제한, JSON 객체 입력, 동일 출처 POST, 호스트 허용 목록, 계획 확인 필수, 정적 파일 허용 목록을 적용합니다.
- 소스 CSV 파일을 HTTP로 직접 제공하지 않습니다. 공개 GitHub에는 다운로드 가능한 압축 원본이 있습니다.
- 서버 분석 질문은 계산을 위해 Vercel 서버로 전송됩니다. 개인정보를 입력하지 마세요. AI 버튼은 별도 전송 동의를 받고 OpenAI와 영구 Redis quota를 사용합니다.
- AI 전역 총량·일일·분당 제한을 영구 Redis로 적용합니다. 부하·장기 가용성 시험은 하지 않았습니다.
- 개발과 검토에 ChatGPT 지원을 활용했습니다. 기본 계산은 AI 없이 동작하며 선택형 분류에서만 AI를 호출합니다.
