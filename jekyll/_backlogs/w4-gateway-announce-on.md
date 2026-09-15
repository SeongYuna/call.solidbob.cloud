---
title: "게이트웨이 알림 3종 켜기 — 검색 중 · 콜 가드 · 필요서류"
assignee: "장민석"
role: "infra"
status: "done"
sprint: 4
priority: 17
date: 2026-09-15
requirement:
  - "B-1"
  - "C-6"
  - "F-2"
paths:
  - "services/gateway/src/main.ts"
---

## 무엇을

`announcePending`·`announceCallGuard`·`announceClosure` 를 켠다. 조건이던 «`apps/call` 실서버 파서» 가 PR #88(frontend `69508ae`)로 main 에 들어왔다 —
`parseRecommendationPending` · `parseCallGuard`(영어 4종) · 새 `parseClosure`(procedure·complete/incomplete). 서버 형식과 맞는지는 같은 날 대조했다.

## 완료 조건

- [x] 켰을 때의 동작은 기존 테스트가 이미 본다 — `gateway` typecheck 통과 · 101 pass
- [x] 게이트웨이 이미지 `0.1.3` → `0.1.4`
- [ ] 운영 반영 뒤 실제 통화에서 화면에 세 신호가 뜨는지(구글 STT 경로 미검증 — `/dev` 경로로 본다)
