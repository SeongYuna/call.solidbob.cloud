---
title: "합성 통화 재생기가 마지막 턴을 잃는다 — 연결 닫는 시점"
assignee: "류준"
role: "ai"
status: "todo"
sprint: 6
priority: 61
date: 2026-09-22
paths:
  - "services/call-mediator/scripts/replay_persona_call.ts"
  - "services/call-mediator/scripts/persona_replay/*"
---

> **정성윤이 09-22 오늘 진행 기록·미결 항목을 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

09-22 운영 SYN-010(류준)에서 마지막 턴(5, 상담원 인사)이 저장되지 않았다(4/5). 같은 날 정성윤 재투입은 5/5, SYN-008 은 16/16.
재생기가 마지막 확정 직후 연결을 닫는 경쟁으로 보인다(가설 — 류준 05번 기록).

## 완료 조건

- [ ] 원인을 찾아 기록한다 — 재생기 쪽이면 마지막 확정의 서버 저장 응답을 기다린 뒤 닫는다
- [ ] 24건 대본을 다시 흘려 저장 건수 = 턴 수 · `e2e_check.py` 가 마지막 턴 누락을 ❌ 로 잡는다
