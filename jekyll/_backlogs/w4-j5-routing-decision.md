---
title: "J-5 인입 전 배정 판정 API + 베테랑 기준 설정"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 4
priority: 20
date: 2026-09-15
requirement:
  - "J-5"
paths:
  - "server/apps/blacklist/adapter/outbound/postgres_agent_routing_adapter.py"
  - "server/apps/blacklist/adapter/outbound/postgres_routing_setting_repository.py"
  - "server/apps/hub/adapter/inbound/api/v1/routing_decision_router.py"
---

## 무엇을

배정 규칙(`route()`)·`routing_log` 는 있었는데 부르는 곳이 없었고, 관리자 설정 탭의 근속 기준을 저장할 곳이 없었다(`decisions/313`, 사용자 선택: 인입 전 API · 후보는 요청으로).

## 완료 조건

- [x] 인터랙터(후보 정리·범위) · 라우터(501·200·404·설정 422·관리자 401) · 어댑터 integration 1
  (블랙리스트 → 6년차 · 기준 5년 저장 후 떨어뜨림 · 블랙리스트 아님 · routing_log 3행 · 없는 통화)
- [x] 마이그레이션 27 → 29(요약 재수정과 한 파일) 새 스키마와 386항목 일치
- [ ] 부르는 곳(교환기·콜 미디에이터) · 운영 반영 · 설정 탭 연결(조서희)
