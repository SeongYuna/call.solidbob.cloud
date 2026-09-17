---
title: "J 블랙리스트 API — 요청·승인·해제 + 고객 식별(HMAC)"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 4
priority: 9
date: 2026-09-14
requirement:
  - "J-1"
  - "J-2"
  - "J-4"
paths:
  - "server/apps/blacklist/adapter/outbound/postgres_blacklist_repository.py"
  - "server/apps/hub/adapter/inbound/api/v1/blacklist_request_create_router.py"
  - "server/apps/hub/adapter/outbound/hmac_customer_ref_adapter.py"
  - "db/generate_schema_docs.py"
depends_on:
  - "w4-blacklist-request-flow"
---

## 무엇을

`server/apps/blacklist` 에 상태 전이 규칙만 있고 저장·HTTP 가 없다(STATE 「J 서버 어댑터·라우터」). 관리자 화면은 mock 이다.
`decisions/304` 로 막혀 있던 셋을 정했다 — 요청자는 `agent_id` 입력 · 승인자는 관리자 로그인(`admin_account.agent_id`) ·
고객은 통화 시작의 발신 번호 HMAC · 만료는 승인할 때 관리자가 일수로.

- `POST /hub/calls` 에 `caller_phone` → `call.customer_id`(HMAC). 콜 미디에이터는 `X-Caller-Phone` 헤더로 넘긴다
- `POST /hub/blacklist-requests` — 근거(콜 가드 건수·온도 이상·통화 길이·마스킹 자막)는 **서버가 DB 에서 모은다**(`decisions/205`)
- 관리자: `GET /hub/blacklist-requests` · `POST /hub/blacklist-requests/{id}/decision` · `GET /hub/blacklist-entries` · `POST /hub/blacklist-entries/{id}/release`

## 완료 조건

- [x] 슬라이스별 인터랙터·라우터 테스트 + 리포지토리 integration
- [x] 평문 번호가 DB·응답·로그 어디에도 없다 · 사유는 저장 전 마스킹
- [ ] `CUSTOMER_REF_HMAC_KEY` 를 `.env.example` 에 사람이 넣는다(보호 훅) — [미결](/open-items/)로 넘긴다
