---
title: "J-5 배정 판정을 누가 부르는가 — 호출 주체와 인증"
assignee: "정성윤"
role: "infra"
status: "todo"
sprint: 7
priority: 78
date: 2026-09-21
requirement:
  - "J-5"
depends_on:
  - "w5-ingest-auth-fail-closed"
paths:
  - "services/call-mediator/*"
---

## 무엇을

`POST /hub/routing-decisions`(J-5 인입 전 배정 판정, `decisions/313`)는 **만들어져 있고 아무도 부르지 않는다.**
시연에서 부를지, 부른다면 누가 어떤 토큰으로 부를지 정한다.

## 왜 정성윤 몫인가

후보가 콜 미디에이터다 — 통화가 시작되는 순간을 아는 것이 거기뿐이다. 09-15 부터 조서희·장민석 님 로그에
**「정성윤 결정 대기」**로 남아 있다.

## 선택지

- `/dev` 테스트 콜이 통화 시작 직후 부른다 → 쓰기 경로 서비스 토큰([w5-ingest-auth-fail-closed](/backlog/w5-ingest-auth-fail-closed/))을 그대로 쓴다
- 시연에서 부르지 않는다 → API 는 있고 **「인입 전 배정은 전화 사업자 연동이 있어야 의미가 있다」**를 발표에 그대로 적는다

## 완료 조건

- [ ] 결정을 `_logs/` 에 남기고 조서희·장민석 님 대기를 푼다
- [ ] 부르기로 하면 — 판정 결과가 상담원 화면 어디에 보이는지까지 조서희 님과 맞춘다
