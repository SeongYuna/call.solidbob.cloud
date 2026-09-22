---
title: "상담원 입사일 저장 API — J-5 가 베테랑을 고를 수 있게"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 6
priority: 61
date: 2026-09-22
requirement:
  - "J-5"
paths:
  - "server/apps/agent_auth/*"
---

## 무엇을

`PUT /admin/agents/{agent_id}/hired-on`(관리자) — 상담원 입사일을 넣는다. `GET /admin/agents` 목록에 `hired_on` 을 싣는다. 근거: `decisions/321`.

## 왜

J-5 는 `agent.hired_on` 으로 근속을 세는데 **입사일을 넣는 길이 없어서** 운영의 모든 상담원이 0년 — 베테랑이 나올 수 없었다.
페르소나 SYN-007(기대값 `routing: veteran`)이 늘 「일반 배정으로 떨어짐」이 된다.

## 완료 조건

- [x] 슬라이스 전 층(schema → router → dto → input port → interactor → output port → adapter → provider → test)
- [x] 없는 상담원·관리자 행 404 · 미래 날짜 422 · null 이면 지움 · 로그인 없음 401 · DB 없음 501 — 테스트
- [x] 실제 PostgreSQL 17 + 현재 `schema.sql` 통합 테스트 통과(로컬 도커)
- [ ] 배포 뒤 시연 상담원 입사일을 넣는다 — 화면이 오기 전에는 API 로(관리자 토큰 필요)
