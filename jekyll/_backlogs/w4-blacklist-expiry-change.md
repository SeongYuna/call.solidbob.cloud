---
title: "블랙리스트 만료 연장·단축 + 이력 — 205 철회, 만료 뒤 재승인 버그"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 4
priority: 15
date: 2026-09-15
requirement:
  - "J-4"
  - "SEC-1"
paths:
  - "server/apps/blacklist/adapter/outbound/postgres_blacklist_repository.py"
  - "server/apps/hub/adapter/inbound/api/v1/blacklist_expiry_change_router.py"
  - "db/migrations/2026-09-15-blacklist-expiry-change.sql"
---

## 무엇을

관리자 화면 연장 버튼이 로컬 전용이었다. `decisions/205` 는 «연장은 새 요청으로만» 이었는데 **그 경로도 막혀 있었다**(만료된 미해제 등록이 부분 유니크 자리를 차지).
사용자 선택으로 205 를 철회하고 관리자 연장·단축 API + 이력 테이블을 만들었다(`decisions/309`). 막힌 재승인도 고쳤다.

## 완료 조건

- [x] 인터랙터 6 · 라우터(401·200·404·409·422) · 리포지토리 integration 1(연장→단축 이력 · 없는 등록 · 만료 뒤 재승인 · 닫힌 등록 409)
- [x] 버그 재현: 승인 시 만료 등록 닫기 한 줄을 빼면 integration 실패 — 넣으면 통과
- [x] 마이그레이션: 26 테이블 DB(HEAD 스키마)에 적용 → 새 `schema.sql` 과 364항목 일치 · 재실행·선행 누락 시 멈춤
- [x] 실제 앱 + postgres:17: 연장 200 → 단축 200 → 이력 2건 → 해제 후 409 · 사유 마스킹
- [ ] 운영 마이그레이션 → 이미지 · 프론트 연결(조서희)
