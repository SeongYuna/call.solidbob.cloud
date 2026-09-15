---
title: "확정된 요약 재수정 + 이력"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 4
priority: 18
date: 2026-09-15
requirement:
  - "D-1"
  - "D-2"
  - "D-3"
depends_on:
  - "w4-summary-confirmation"
paths:
  - "server/apps/hub/adapter/outbound/postgres/summary_revision_repository.py"
  - "db/migrations/2026-09-15-summary-revision-app-setting.sql"
---

## 무엇을

확정은 한 번이라 틀린 확정을 고칠 길이 없었다(`decisions/310` 남는 것). 사유와 함께 고치고 이전 값을 남긴다(`decisions/311`).

## 완료 조건

- [x] 인터랙터 5 · 라우터 3 · 리포지토리 integration 1(확정 전 409 · 이전 값 이력 · 후속조치 superseded · 두 번 고치면 이력 2건)
- [x] 마이그레이션 27 → 28 이 새 스키마와 377항목 일치 · 재실행·선행 누락 시 멈춤
- [x] 실제 앱 E2E: 확정 전 409 → 확정 → 재수정(마스킹) → 이력 → record 에 superseded/confirmed
- [ ] 운영 마이그레이션 → 이미지 · 프론트 연결(조서희)
