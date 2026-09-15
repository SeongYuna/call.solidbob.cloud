---
title: "상담원 전용 토큰 — 블랙리스트 요청자를 본문이 아니라 토큰에서"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 4
priority: 12
date: 2026-09-15
requirement:
  - "J-1"
  - "SEC-1"
depends_on:
  - "w4-blacklist-api"
paths:
  - "server/apps/agent_auth/*"
  - "server/apps/hub/adapter/inbound/api/v1/blacklist_request_create_router.py"
  - "db/migrations/2026-09-15-agent-token.sql"
---

## 무엇을

`POST /hub/blacklist-requests` 가 `requested_by` 를 본문으로 받아 **아무 상담원 ID 로나 요청할 수 있었다**(`decisions/304` 남은 것).
상담원 전용 토큰으로 막는다(`decisions/307`, 사용자 선택).

- `agent_token` 테이블 — **해시만 저장**. 원문 `cga_…` 는 발급 응답에 한 번
- 관리자 API: `POST·GET /admin/agent-tokens` · `POST /admin/agent-tokens/{id}/revoke`
- `require_agent` 가드 → 블랙리스트 요청의 요청자

## 완료 조건

- [x] 인터랙터 9 · 라우터 5 · 블랙리스트 라우터 5 · 리포지토리 integration 1 — `server` 696 passed + integration 12 · 계약 4종 KEPT
- [x] 마이그레이션: 25 테이블 DB 에 적용 → 새 `schema.sql` 과 349항목 일치 · 재실행·선행 누락 시 멈춤 확인
- [x] 실제 앱 + postgres:17: 토큰 없음 401 · 본문 `requested_by` 무시 · 폐기 후 401
- [ ] 운영: 마이그레이션 → 이미지 순서로 적용 (정성윤 — 인스턴스 접근)
- [ ] 프론트: `Authorization` 헤더·`requested_by` 제거 · 관리자 발급 화면 (조서희)
