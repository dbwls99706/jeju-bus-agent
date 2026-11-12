# 버스여울 화면 디자인 참고

기존 큰 글씨·키보드·대비·계획 확인 기능을 보존하면서 시각 계층을 정리했습니다. 외부 코드를 내려받아 실행하거나 새 UI 프레임워크를 설치하지 않았습니다.

## 공개 디자인 시스템 참고

- IBM Carbon Design System, Spacing: https://www.carbondesignsystem.com/building-blocks/foundations/spacing/overview
  - 2·4·8 단위 간격 체계와 여백을 통해 관계와 계층을 표현한다는 원칙을 참고했습니다.
- GOV.UK Design System, Button: https://design-system.service.gov.uk/components/button/
  - 버튼이 수행할 동작을 명확히 적고, 주 행동과 보조 행동을 구분해 다음 단계를 찾기 쉽게 한다는 원칙을 참고했습니다.
- WCAG 2.2 및 고령 사용자 고려사항: `ACCESSIBILITY.md`.

Carbon 및 GOV.UK는 공개 디자인 시스템을 참고한 출처입니다. 해당 컴포넌트 코드를 앱에 복제하거나 패키지 의존성으로 도입했다는 의미는 아닙니다. 앱 CSS·SVG는 프로젝트에서 직접 작성했습니다. 특정 브랜드의 공식 제품·인증·후원으로 표현하지 않습니다.

## 보존 사항

통계 계산과 질문 범위 검증은 바꾸지 않습니다. 브랜드 SVG 아이콘, 18px 기본 글자, 17px 보조 설명, 48px 이상 주요 조작, 키보드 초점과 움직임 줄이기 대응을 유지합니다. 장식 효과보다 실제 결과와 제한조건의 읽기 쉬움을 우선합니다. 데이터 미기록을0으로 간주하지 않으며 원기간 비교와 요일표준화의 다른 의미를 유지합니다.
