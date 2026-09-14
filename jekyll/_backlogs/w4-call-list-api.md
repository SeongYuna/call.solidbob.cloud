---
title: "통화 이력 목록 GET /hub/calls"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 4
priority: 8
date: 2026-09-14
requirement:
  - "D-1"
  - "D-2"
paths:
  - "server/apps/hub/adapter/inbound/api/v1/call_list_router.py"
  - "server/apps/hub/adapter/outbound/postgres/call_list_repository.py"
---

## 무엇을

대시보드 상담기록 패널(`CallHistoryPanel`)이 `GET /hub/calls` 가 없어 mock 목록을 쓴다. 자막 재조회
(`GET /hub/calls/{id}/transcript`)는 이미 있다. `call` 테이블을 최근 시작순으로 페이지 조회한다.

- `customer_id` 필터를 함께 둔다 — 재상담 고객 이력(A-5 목록)이 같은 조회다.
  ⚠ **다만 `call.customer_id` 를 채우는 경로가 없다**(`POST /hub/calls` 가 받지 않는다, F-3 미정) — 필터는 지금 늘 빈 결과다

## 완료 조건

- [x] 인터랙터·라우터·리포지토리(가짜 + integration) 테스트
- [x] DB 미설정이면 501 — 빈 목록을 «통화가 없다» 로 돌려주지 않는다
