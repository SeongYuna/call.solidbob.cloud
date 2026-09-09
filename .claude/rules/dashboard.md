---
paths:
  - "apps/dashboard/**/*.tsx"
  - "apps/dashboard/**/*.ts"
---

# 프론트엔드 규칙 (apps/dashboard)

CallGuard 상담원 대시보드는 React(웹)다 ([팀 분업](/docs/07/): 조서희 담당 — 2026-08-26
팀 개편 이전에는 장민석 담당이었으나, 장민석이 백엔드·AI로 옮기고 조서희가 신규 합류해
프론트엔드를 전담한다. `_project/decisions/005`). 앱(Flutter)은 개발하지 않는다.
`apps/dashboard`는 상담원 화면이다. 자막(좁게) | 이용약관·충족요건(넓게).
고객 화면(`apps/customer`)은 `_project/decisions/014` 로 철회했다.

---

## 1. 기본

- TypeScript strict 모드. `any` 남용 금지 — WebSocket으로 받는 이벤트(전사/카드/종결)는
  [7.3절 인터페이스 계약](/docs/07/)의 스키마 타입으로 파싱해서 쓴다.
- 상태관리는 팀 내 합의된 단일 방식으로 통일한다 — 화면마다 다른 방식을 섞지 않는다.
  아직 미정이면 새로 도입하기 전에 팀에 먼저 확인한다.

## 2. 화면 구조 — 자막 | 이용약관·충족요건

상단 2분할: 실시간 자막(`1fr`) | 이용약관·충족요건 통합 패널(`1.6fr`).
마스킹된 자막 줄에만 「⚠ 경고」 태그를 붙인다. P1~P7 코드는 화면에 내지 않는다.
오른쪽 패널 상단은 칩 세 개(콘텐츠 보기 · 도메인 · 상담기록)다. 「팝업창」은 카드 본문만,
「충족요건」은 종결 체크리스트만 보여 준다. 「상담기록」은 목록만 연다. 항목을 고르면
왼쪽 자막 패널이 그 기록을 보여 주고, 실시간 발화는 스토어에 그대로 쌓인다.
종결 모달은 쓰지 않는다.

```tsx
// Requirement: B-5
interface RecommendationCard {
  title: string;
  summary: string;
  source: { doc: string; clause: string };  // 출처는 항상 존재해야 함
  score: number;                            // 유사도
}
```

- `source` 필드는 항상 표시해야 한다 — 근거 없는 카드를 렌더링하지 않는다 ([B-6](/docs/02/)).
- 추천 카드는 오른쪽 패널에 세로로 쌓는다. 하단에는 진행 중인 종결 탭만 두고,
  클릭하면 해당 카드로 스크롤한다 (`_project/decisions/014`).
- 화면 어디에도 위험도 점수나 "안전합니다" 류 표현을 하드코딩하지 않는다 ([부록 A-1](/docs/12/)).
- 카드가 `closure_type`과 연결된 경우 「충족요건」 뷰에 체크리스트를 보여 준다.
  연결되지 않은 카드는 이 탭 목록에서 빼 는다. 연결된 카드가 하나도 없으면
  패널에 「충족요건이 필요한 처리가 아직 없습니다」만 둔다. 여러 건이면 전부 표시한다.
  미충족 항목에만 「지금 할 말」과 항목별 근거 조항을 붙인다 — 판정(true/false)은
  바꾸지 않는다. 근거가 전부 충족되면 「종결 처리」 버튼이 나타난다(충족요건 뷰에만).
  미충족이면 버튼을 두지 않거나 비활성.
  카피는 「근거 N/M 충족」처럼 관찰만 한다
  ([2.7절 주장 범위](/docs/02/), [2.8절 단방향 경고](/docs/02/)).

## 3. API·WebSocket 통신

- `services/gateway`(WebSocket)와 `fastapi`(REST) 호출은 각각 단일 클라이언트
  모듈(`lib/ws/gatewayClient.ts`, `lib/api/coreClient.ts`)로 모으고, 컴포넌트에서 직접
  소켓/HTTP 호출을 흩뿌리지 않는다.
- 에러 메시지는 한국어로, 사용자에게 서버 내부 정보(스택트레이스 등)를 노출하지 않는다.

## 4. 테스트

- `apps/dashboard/test/`에 컴포넌트 테스트 — 상세 규칙은 `.claude/rules/testing.md` 참고.

## 5. 배포 전제 — `docs/infra-runbook.md`

운영 인프라는 단일 EC2 + k3s + Caddy 다. **API 주소나 WebSocket 엔드포인트를 정하기 전에 런북 16-2·18장을 읽는다.**

- 프론트가 붙는 주소는 **`https://server.solidbob.cloud` 하나**다(16-2·18). Caddy 가 443 만 열고 나머지는
  클러스터 내부 ClusterIP 라, `elasticsearch:9200`·`ollama:11434` 를 브라우저에서 직접 부를 수 없다.
- Cloudflare 는 **DNS 전용(회색 구름)** 이다(18장). 프록시를 켜면 Let's Encrypt 인증서 발급이 끊긴다 —
  DNS·인증서에 걸리는 문제는 정성윤에게 넘긴다.
- 개발은 로컬 `infra/docker-compose.yml`(PostgreSQL·ES) + `server/` 로 띄운다. **운영 주소를 개발 기본값으로 굳히지 않는다** —
  주소는 환경변수로 빼고, 로컬 기본값은 로컬 것으로 둔다.
- ⚠ `services/gateway`(WebSocket)는 **아직 코드가 0줄**이다(`_project/STATE.md`). 게이트웨이 주소는 확정되지 않았으므로
  `lib/ws/gatewayClient.ts` 에 엔드포인트를 상수로 박기 전에 확인한다.
