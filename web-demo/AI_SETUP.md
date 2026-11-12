# AI 준비 상태와 비용 제한

현재 공개 웹은 규칙 기반입니다. `OPENAI_API_KEY`를 등록해도 유료 호출은 자동 활성화되지 않습니다. `openai_planner.py`와 `quota.py`는 준비 모듈이며 아직 웹 요청에 연결하지 않았습니다.

## 등록 위치

Vercel 프로젝트 → Settings → Environment Variables → Production. 키는 Secret으로 직접 등록하고 Git·채팅·브라우저 클라이언트에 넣지 않습니다.

- `OPENAI_API_KEY`: OpenAI 프로젝트 전용 키
- `AI_ENABLED=0`: 현재 값 유지. 영구 quota 및 명시적 AI 경로 검증 뒤에만 전환
- `DATA_MODE=real`: 현재 실제 집계 자료 유지
- `QUOTA_REDIS_REST_URL`: 영구 Redis의 HTTPS REST origin
- `QUOTA_REDIS_REST_TOKEN`: 해당 Redis REST 자격증명, Secret
- `QUOTA_NAMESPACE`: 한 프로젝트의 승인 예산 동안 변경하지 않는 식별자
- `QUOTA_LIFETIME_LIMIT`, `QUOTA_DAILY_LIMIT`, `QUOTA_MINUTE_LIMIT`: 양의 정수, 분당 ≤ 일일 ≤ 총량

## 원자적 제한

OpenAI 호출 전 Redis 단일 Lua EVAL로 전역 총량·일일·분당 한도를 검사하고 한 번 예약합니다. 오류나 응답 유실이면 AI를 호출하지 않으며 예약 반환·자동 재시도도 없습니다. 프로세스 메모리나 Vercel 임시 파일은 총량 저장소로 쓰지 않습니다. namespace를 바꾸거나 Redis 키를 지우거나 저장소가 초기화되면 한도가 리셋될 수 있으므로 금지합니다. 데이터 영속성·계정 유지 조건은 저장소에서 별도 확인해야 합니다.

## 모델·요청 제한

준비 모듈은 고정 `gpt-6-luna`, Responses API, reasoning none, 출력 최대128 tokens, 질문 최대300자/1,200 UTF-8바이트입니다. 질문 분류만 수행하고 실제 수치·CSV는 OpenAI에 보내지 않습니다. 외부 엔드포인트 변경·리다이렉트·자동 재시도는 금지합니다.

공식 참고: https://developers.openai.com/api/docs/models/gpt-6-luna 및 https://developers.openai.com/api/docs/pricing

비용은 호출 수뿐 아니라 모델 가격·실제 토큰·다른 서비스 사용액에도 달려 있습니다. 이 모듈은 전체 계정의 기존 청구액, 다른 앱 호출, Redis/Vercel 요금을 자동 차감하지 않습니다. 따라서 이것만으로 프로젝트의 총 달러 지출을 보장하지 않습니다. 승인 예산에서 기존/기타 비용을 제외한 AI 예산을 정하고 보수적인 호출 한도로 변환해야 합니다.

현재 테스트는 HTTP/Redis 응답 mock 기반이며 실제 Redis Lua 실행·실제 OpenAI 응답은 별도 검증이 필요합니다. 키 내용은 읽거나 출력하지 않습니다.
