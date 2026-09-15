---
title: "통화 후 초안 501 걷기 — D-1~D-3 규칙 발췌 스포크"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 4
priority: 11
date: 2026-09-15
requirement:
  - "D-1"
  - "D-2"
  - "D-3"
depends_on:
  - "w7-postcall-contract"
paths:
  - "server/apps/postcall/*"
  - "server/apps/hub/dependencies/postcall_provider.py"
---

## 무엇을

`POST /hub/calls/{call_id}/close` 가 501 이라 프론트 통화 후 화면을 붙일 수 없었다. 요약 LLM 은 운영에 없다.
**LLM 없이 규칙 발췌 초안**으로 먼저 연다(`decisions/306`, 사용자 선택).

- D-1: 고객 첫 실질 발화 + 그 뒤 상담원 안내 + 발화 건수 — **자막에서 고른다, 쓰지 않는다**
- D-2: `null` — 유형을 가를 규칙표가 없다
- D-3: 상담원의 「…드리겠습니다」 약속 중 연락·발송·접수 류

## 경계

LLM 요약은 [w7-postcall-spoke](/backlog/w7-postcall-spoke/)(류준)로 그대로 남는다 — 들어오면 프로바이더만 바꾼다.
저장은 [w7-postcall-persistence](/backlog/w7-postcall-persistence/)로 남는다.

## 완료 조건

- [x] 501 이 사라지고 `/health` `spokes` 에 `postcall`
- [x] 도메인 11 · 어댑터 2 테스트 — 발췌 문장이 전부 자막에 있다는 것을 고정 · `server` 696 passed · 계약 4종 KEPT
- [x] 실제 앱 + postgres:17 에서 마스킹본만 발췌됨을 확인(2026-09-15)
- [ ] 품질 측정 — 골든셋 D 케이스 0건이라 **측정 불가**
