---
title: "배정 판정 결과를 화면에 보인다 — 지금은 미디에이터 로그만"
assignee: "조서희"
role: "app"
status: "todo"
sprint: 6
priority: 73
date: 2026-09-22
requirement:
  - "J-5"
paths:
  - "apps/admin/src/*"
  - "apps/call/src/*"
depends_on:
  - "w7-j5-routing-caller"
---
> **정성윤이 09-22 저녁 최종 QA(류준 페르소나 4 + 검증 웨이브)·운영 확인 결과를 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

J-5 배정 판정은 통화 시작 직후 미디에이터가 부른다(PR #131). 결과(`veteran` / 일반 배정 / 블랙리스트)는 로그와 `routing_log` 에만 있고 화면에 없다.
어디에 어떤 말로 보일지 장민석 님과 정한다 — 「배정 판정」으로 부르고, 연결을 바꾸지 못한다는 한계는 표시하지 않는다(`decisions/320`).

## 완료 조건

- [ ] 표시 위치·문구 합의(관리자 통화 상세 또는 상담원 통화 시작 배너)
- [ ] `routing_log` 를 읽는 API 가 필요하면 장민석 님 티켓으로 쪼갠다
- [ ] 시연 SYN-006 → SYN-007 에서 `veteran` 이 화면에 보인다

근거: `w7-j5-routing-caller` 「남은 것 ②」.
