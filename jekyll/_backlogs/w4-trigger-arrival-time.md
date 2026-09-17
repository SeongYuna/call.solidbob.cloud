---
title: "트리거 발동 시각을 실제 도착 시각으로 — 콜 미디에이터 received_at_ms"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 4
priority: 3
date: 2026-09-14
requirement:
  - "B-1"
  - "A-1"
paths:
  - "services/call-mediator/src/app/call_registry.ts"
  - "services/call-mediator/src/app/ports.ts"
  - "server/apps/hub/app/dtos/transcript_dto.py"
  - "server/apps/hub/adapter/inbound/api/schemas/recommendation_schema.py"
  - "ai/apps/retrieval/adapter/outbound/is_final_trigger.py"
---

## 무엇을

`TranscriptEvent` 에 **이벤트 도착 시각이 없어** 트리거 발동 시각을 «발화 종료 + 346ms» 상수로 모형화하고 있다
([미결](/open-items/) 2026-08-27 항목). 실시간 경로가 생겼으니 콜 미디에이터가 STT final 을 **받은 시각**
(`received_at_ms`, 통화 시작 기준 ms)을 `POST /hub/recommendations` 에 실어 보내고, 트리거가 그 값을 쓴다.

## 완료 조건

- [x] 콜 미디에이터가 final 을 받은 시각을 `received_at_ms` 로 보낸다 (테스트)
- [x] 서버 `RecommendRequest` → `TranscriptEvent.received_at_ms` 로 전달 (테스트)
- [x] `IsFinalTrigger` 가 `received_at_ms` 가 있으면 그 값을 쓴다, 없으면 기존 모형 (테스트)
- [x] 평가 하네스는 그대로 «측정 불가» — 골든셋에 도착 시각이 없다(절대 원칙 10)
