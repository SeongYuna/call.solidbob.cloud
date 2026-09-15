---
title: "추천 저장 + 카드 card_id — 카드 피드백을 부를 수 있게"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 4
priority: 13
date: 2026-09-15
requirement:
  - "B-5"
  - "E-1"
paths:
  - "server/apps/hub/adapter/outbound/postgres/recommendation_repository.py"
  - "server/apps/hub/app/ports/output/recommendation_record_port.py"
---

## 무엇을

`POST /hub/cards/{card_id}/feedback` 이 있는데 추천 응답에 `card_id` 가 없어 프론트가 못 불렀다. 원인은 **추천을 저장하지 않는 것**이었다.
발동한 추천을 `recommendation`·`recommendation_card` 에 남기고 돌아온 id 를 카드에 싣는다(`decisions/308`).

## 완료 조건

- [x] 인터랙터 5 · 라우터 3 · 리포지토리 integration 1 — 지연은 저장 전에 잰다 · 없는 조항 NULL · 없는 통화 404
- [x] `server` 719 passed · integration 14 · 계약 4종 KEPT / `ai` 통과
- [x] 실제 앱 + postgres:17: 통화 없이 404 → 추천 `card_id "1"` → 그 id 로 피드백 201
- [ ] 운영 반영(다음 서버 이미지) · 실시간 경로 지연 증가분 측정 — 미측정
