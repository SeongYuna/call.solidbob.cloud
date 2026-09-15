---
title: "후속조치 저장 — follow_up_action 이 비어 있다"
assignee: "장민석"
role: "ai"
status: "todo"
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

- [ ] `follow_up_action` 저장 어댑터 + 포트 등록
- [ ] `call.summary_text`(D-1) · `call.inquiry_type`(D-2)도 함께 저장된다
- [ ] **마스킹 완료본만 저장된다** — 스키마에 원문 컬럼이 없는 것을 확인한다(SEC-1)
- [ ] `cd server && pytest` 통과 · 계약 KEPT
