---
title: "관리자 현황판 집계 API — GET /hub/admin-stats"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 6
priority: 76
date: 2026-09-22
requirement:
  - "J-3"
  - "J-5"
  - "C-6"
paths:
  - "server/apps/hub/adapter/inbound/api/v1/admin_stats_router.py"
  - "server/apps/hub/adapter/outbound/postgres/admin_stats_repository.py"
---

## 무엇을

관리자 현황판(`apps/admin` `WallboardTab`)의 숫자를 **한 번의 조회로** 주는 서버 API. 조서희 님이 「장민석 6번」으로 기다리던 것.

## 왜

현황판 네 칸이 mock 이거나, 목록 API 를 `limit=1` 로 불러 `total` 만 쓰고 있었다(통화 목록은 무인증). J-5 배정 판정(`routing_log`)은 셀 곳이 없었다 —
`decisions/126` 으로 콜 미디에이터가 배정 판정을 부르게 되면 값이 생긴다.

## 한 것 (2026-09-22)

- `GET /hub/admin-stats` — 관리자 로그인 필요(`require_admin`), DB 없으면 501(0 을 지어내지 않는다), 응답 전부 문자열
- 여덟 칸: `calls_total` · `calls_closed` · `call_guard_flags` · `pending_requests` · `active_entries` · `routing_decisions` · `routing_blacklisted` · `routing_fell_back` + `counted_at`
- 문장 하나로 센다(같은 스냅샷). **상담원 단위 숫자는 없다**(부록 A-1) — 테스트로 고정
- ⚠ 「완료 통화」는 이제 `calls_closed`(`/close` 로 닫힌 통화)다. 09-20 이전 통화는 닫힌 적이 없어 `calls_total` 보다 작다

## 남은 것

- 화면 연결은 조서희 님 — `WallboardTab` 이 이 API 하나를 부르게. 「완료 통화 누적」에 무엇(`calls_total`/`calls_closed`)을 보일지는 화면이 정한다
- `routing_*` 는 부르는 곳(`w7-j5-routing-caller`)이 붙기 전엔 0 이다
