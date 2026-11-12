# AI 준비 상태와 비용 제한

공개 웹은 기본 규칙 기반이며 별도 동의 체크박스와 AI 버튼으로 `gpt-6-luna` 분석종류 분류를 실행할 수 있습니다. 키만 등록해서는 활성화되지 않으며 명시적 AI_ENABLED와 영구 quota 설정이 모두 필요합니다. 2026-11-12 공개 브라우저에서 실제 Luna 응답 1회→계획 승인→Python 집계를 검증했습니다.

## 등록 위치

Vercel 프로젝트 → Settings → Environment Variables → Production. 키는 Secret으로 직접 등록하고 Git·채팅·브라우저 클라이언트에 넣지 않습니다.

- `OPENAI_API_KEY`: OpenAI 프로젝트 전용 키
- `AI_ENABLED=1`: 운영에 명시 활성화. 끄려면 0으로 바꾸고 재배포
- `DATA_MODE=real`: 현재 실제 집계 자료 유지
- `QUOTA_REDIS_REST_URL`: 영구 Redis의 HTTPS REST origin. Vercel 연동의 `KV_REST_API_URL`도 지원
- `QUOTA_REDIS_REST_TOKEN`: 해당 Redis REST 자격증명, Secret. Vercel 연동의 `KV_REST_API_TOKEN`도 지원
- `QUOTA_NAMESPACE`: 한 프로젝트의 승인 예산 동안 변경하지 않는 식별자
- `QUOTA_LIFETIME_LIMIT`, `QUOTA_DAILY_LIMIT`, `QUOTA_MINUTE_LIMIT`: 양의 정수, 분당 ≤ 일일 ≤ 총량

## 원자적 제한

OpenAI 호출 전 Redis 단일 Lua EVAL로 전역 총량·일일·분당 한도를 검사하고 한 번 예약합니다. 오류나 응답 유실이면 AI를 호출하지 않으며 예약 반환·자동 재시도도 없습니다. 프로세스 메모리나 Vercel 임시 파일은 총량 저장소로 쓰지 않습니다. namespace를 바꾸거나 Redis 키를 지우거나 저장소가 초기화되면 한도가 리셋될 수 있으므로 금지합니다. 데이터 영속성·계정 유지 조건은 저장소에서 별도 확인해야 합니다.

## 모델·요청 제한

준비 모듈은 고정 `gpt-6-luna`, Responses API, reasoning none, 출력 최대128 tokens, 질문 최대300자/1,200 UTF-8바이트입니다. 질문 분류만 수행하고 실제 수치·CSV는 OpenAI에 보내지 않습니다. 외부 엔드포인트 변경·리다이렉트·자동 재시도는 금지합니다.

공식 참고: https://developers.openai.com/api/docs/models/gpt-6-luna 및 https://developers.openai.com/api/docs/pricing

비용은 호출 수뿐 아니라 모델 가격·실제 토큰·다른 서비스 사용액에도 달려 있습니다. 이 모듈은 전체 계정의 기존 청구액, 다른 앱 호출, Redis/Vercel 요금을 자동 차감하지 않습니다. 따라서 이것만으로 프로젝트의 총 달러 지출을 보장하지 않습니다. 승인 예산에서 기존/기타 비용을 제외한 AI 예산을 정하고 보수적인 호출 한도로 변환해야 합니다.

58개 단위·회귀 검사 통과와 별도로, 운영 Redis 예약 성공 뒤 실제 OpenAI 분류 응답 및 계획 승인 후 7시간대 집계까지 검증했습니다. 키 내용은 읽거나 출력하지 않습니다.

운영 설정: namespace `busyeoul-review-202611`, 총 20,000회·UTC일 1,000회·분 10회. 이 값을 넘는 설정은 코드에서도 거부합니다. 승인된 프로젝트 총 $100 가운데 AI 호출은 보수적으로 회당 $0.001 예약 상당, 총 $20 이하를 목표로 배정했습니다. 이것은 모델 단가 유지와 설정 무변경을 전제로 한 보수적 계산이며, 별도 계정·서비스의 지출까지 통제하는 결제 상한은 아닙니다. Upstash Free(월 500,000 commands)와 Vercel Hobby를 사용합니다.
