---
title: "콜 가드 로그 조회 GET /hub/call-guard-flags (관리자)"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 4
priority: 10
date: 2026-09-14
requirement:
  - "C-6"
paths:
  - "server/apps/hub/adapter/inbound/api/v1/call_guard_flag_list_router.py"
depends_on:
  - "w4-call-guard-wiring"
---

## 무엇을

관리자 화면 콜 가드 로그(`CallGuardLogEntry`)가 mock 이다. [w4-call-guard-wiring](/backlog/w4-call-guard-wiring/)이
`call_guard_flag` 에 쌓기 시작했으니 최근순으로 읽는다. 관리자 로그인이 필요하다 — 잡힌 표현이 고객 발화다.

⚠ 갈래 이름이 다르다 — 서버는 `insult·threat·sexual·distress`(MANUAL-5장), 프론트 mock 은 `폭언·욕설·위협`.
서버는 정본(DDL CHECK)대로 보내고, 화면 표기는 조서희 님이 옮긴다.

## 완료 조건

- [x] 인터랙터·라우터·리포지토리(integration) 테스트 · 로그인 없으면 401
