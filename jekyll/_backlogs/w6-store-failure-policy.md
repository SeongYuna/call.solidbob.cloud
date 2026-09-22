---
title: "저장 실패 정책 — 화면에 나가는 판정은 기록 실패로 사라지지 않게"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 6
priority: 79
date: 2026-09-22
requirement:
  - "B-1"
  - "F-2"
  - "C-6"
paths:
  - "server/apps/hub/app/use_cases/recommendation_interactor.py"
  - "server/apps/hub/app/use_cases/required_docs_detection_interactor.py"
---

## 무엇을

저장 실패(우리 쪽 DB 흔들림)를 경로마다 다르게 다루고 있다(09-22 사후 검토) — 콜 가드·컴플라이언스는 「200 + 로그」,
추천·필요서류 판정은 500. 정책을 정하고 맞춘다.

## 완료 조건

- [ ] 결정 기록(`3xx`) — 어떤 경로가 삼키고 어떤 경로가 5xx 인지 한 줄 규칙으로
- [ ] 바꾼 경로마다 「저장 실패 → 결과는 나간다 + 로그」 테스트 · 호출자 실수(없는 통화 등)는 그대로 4xx 테스트

---

> **2026-09-22 장민석 — 정했다(`_project/decisions/318`).** 화면에 나가는 판정(추천·필요서류 자동 판정·체크리스트 판정)은 기록 실패해도 결과를 돌려주고
> 경고 로그(예외 타입만) — 추천은 `card_id` null. 저장이 목적인 경로(전사·통화 시작·요약 확정·블랙리스트)는 5xx 그대로. 없는 통화는 셋 다 404 —
> 필요서류 판정 저장소가 원시 FK 오류(500)를 올리던 것을 `CallNotStartedError` 로 바로잡았다(실제 DB 테스트). 인터랙터 테스트 6건 · 라우터 404 테스트 2건.
