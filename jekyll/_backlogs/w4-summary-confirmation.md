---
title: "통화 후 요약 확정 — 상담원이 초안을 고쳐서 확정"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 4
priority: 16
date: 2026-09-15
requirement:
  - "D-1"
  - "D-2"
  - "D-3"
depends_on:
  - "w7-postcall-persistence"
paths:
  - "server/apps/hub/adapter/inbound/api/v1/summary_confirmation_router.py"
  - "server/apps/hub/adapter/outbound/postgres/summary_confirmation_repository.py"
---

## 무엇을

요약 초안을 확정하는 API 가 없어 모든 요약이 영원히 초안이었다. 상담원이 고쳐서 확정한다(`decisions/310`, 사용자 선택).

## 완료 조건

- [x] 인터랙터 5 · 라우터 4(401·501·200·404/409/422) · 리포지토리 integration 1(초안 → 확정 → 재확정·재초안 409)
- [x] 고친 문구 마스킹 · 누가 확정했는지 저장 안 함 · 스키마 변경 없음
- [ ] 운영 반영(서버 `0.1.10`) · 프론트 연결(조서희)
