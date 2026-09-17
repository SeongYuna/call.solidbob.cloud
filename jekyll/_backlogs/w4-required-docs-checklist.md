---
title: "F-2 필요서류 체크리스트 — 다산 규칙표 25개 + 자동 안내 판정"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 4
priority: 11
date: 2026-09-14
requirement:
  - "F-2"
  - "B-1"
paths:
  - "server/apps/closure_gate/domain/value_objects/closure_rule.py"
  - "server/apps/closure_gate/domain/services/detection.py"
  - "server/apps/hub/adapter/inbound/api/v1/required_docs_detection_router.py"
depends_on:
  - "w4-schema-qa-followup"
---

## 무엇을

`decisions/305`. 금융·쇼핑 종결 게이트를 다산 필요서류 체크리스트로 다시 만들었다.

- 규칙표: `TERM.md` 필요서류 조항 35개 중 **조건 없는 25개** — 나머지는 `EXCLUDED` 에 이유와 함께
- 판정 `complete`/`incomplete`(rev.5 경고) · 조건부 서류는 `conditional` 로만
- 자동 판정: 상담원 확정 발화(마스킹본) 키워드 → `POST /hub/required-docs-checks` · 콜 미디에이터가 추천 1순위 조항을 절차로 잡는다
- 스키마 `closure`(헤더) + `closure_item`(항목)

## 완료 조건

- [x] 규칙표 ↔ 조항 원문 대조 테스트 · 판정·자동 판정·라우터·저장(integration) 테스트
- [x] 콜 미디에이터 자동 판정(대시보드 전송 기본 꺼짐)
- [ ] ⚠ **판정 정확도 측정 불가** — 골든셋 필요서류 케이스 0건. 류준 님께 넘긴다
