---
title: "C-6 콜가드 배선 — POST /hub/call-guard-checks + 저장 + 콜 미디에이터 전달"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 4
priority: 7
date: 2026-09-14
requirement:
  - "C-6"
paths:
  - "server/apps/hub/adapter/inbound/api/v1/call_guard_check_router.py"
  - "server/apps/hub/adapter/outbound/postgres/call_guard_flag_repository.py"
  - "ai/provider.py"
  - "services/call-mediator/src/app/call_registry.ts"
---

## 무엇을

`ai/apps/call_guard`(규칙 탐지기)와 서버 `CallGuardPort`·`call_guard_flag` 테이블은 있는데 **잇는 길이 없다.**
프론트는 mock·자체 판정으로만 콜가드를 띄운다.

- 서버 슬라이스 `call_guard_check` — `POST /hub/call-guard-checks`(마스킹된 고객 발화) → 탐지 → `call_guard_flag` 저장
- 합성 루트가 `ai/` 구현체를 꽂는다(`/health` spokes 에 `call_guard`)
- 콜 미디에이터가 고객 final 마다 부른다. 대시보드 전송(`call_guard` 메시지)은 **기본 꺼 둔다** — 프론트 파서 수신 대기

## 완료 조건

- [x] 인터랙터·라우터·리포지토리(가짜 커넥션 + integration) 테스트
- [x] `phrase`·`span` 은 마스킹된 본문 기준 (MANUAL-5.5)
- [x] 콜 미디에이터 테스트 · §7.3 계약 문서
