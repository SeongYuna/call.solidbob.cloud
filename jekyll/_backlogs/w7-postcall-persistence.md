---
title: "후속조치 저장 — follow_up_action 이 비어 있다"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 7
priority: 75
date: 2026-09-15
requirement:
  - "D-3"
depends_on:
  - "w7-postcall-contract"
paths:
  - "server/apps/hub/adapter/outbound/*"
---

## 무엇을

`POST /hub/calls/{call_id}/close` 가 돌려준 **후속조치를 `follow_up_action` 테이블에 저장**한다.

## 왜 남아 있나

[w7-postcall-contract](/backlog/w7-postcall-contract/)의 마지막 줄이 그대로 남은 것이다 —
*"`follow_up_action` 테이블 저장은 영속성 계층 뒤에 붙인다."*
테이블은 **이미 있다**(`db/schema.sql`). 없는 것은 어댑터다.

## 담당을 갈라 둔 이유

요약을 **만드는 것**은 `ai/`([w7-postcall-spoke](/backlog/w7-postcall-spoke/), 류준),
**저장하는 것**은 `server/`(장민석)다. `CLAUDE.md` §4 — 티켓 하나에 두 사람의 작업을 담지 않는다.
⚠ 디렉터리는 잠겨 있지 않다(`decisions/302`) — 한 사람이 둘 다 해도 되지만, **그때는 티켓을 넘겨받았다고 본문에 적는다.**

## 완료 조건

- [x] `follow_up_action` 저장 어댑터 + 포트 등록 — `PostcallRecordPort` · `postgres/postcall_repository.py` · DB 없으면 로그 어댑터
- [x] `call.summary_text`(D-1) · `call.inquiry_type`(D-2)도 함께 저장된다 — `summary_confirmed_at` 은 건드리지 않는다(NULL = 초안)
- [x] **마스킹 완료본만 저장된다** — 초안이 마스킹된 자막에서만 발췌된다(`decisions/306`). `call`·`follow_up_action` 에 원문 컬럼 없음
- [x] `cd server && pytest` 698 passed · integration 13 · 계약 4종 KEPT (2026-09-15)

## 2026-09-15 — 구현 (장민석)

- 다시 닫으면 **확정 전 초안만 교체**한다 — 지우는 후속조치는 `status = 'draft'` 인 것뿐, 상담원이 손댄 항목은 남는다
- **확정된 요약은 덮지 않는다** — `summary_confirmed_at` 을 행 잠금으로 읽고 채워져 있으면 409. 통화가 없으면 404
- 실제 앱 + postgres:17: 없는 통화 404 → 통화 시작 → 저장 200 → 재요청 후 후속조치 1행 유지 → 확정 뒤 409
- ⚠ 남은 것: 저장한 요약을 **읽는 경로가 없다** — `GET /hub/calls` 는 `inquiry_type`·`summary_confirmed` 만 주고 `summary_text`·후속조치는 안 준다. 상담원 확정 API 도 없다
