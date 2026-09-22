---
title: "통화 기록 응답에 `customer_id` 를 싣는다 — 조서희 님 요청"
assignee: "장민석"
role: "ai"
status: "todo"
sprint: 6
priority: 72
date: 2026-09-22
paths:
  - "server/apps/hub/*"
---
> **정성윤이 09-22 저녁 최종 QA(류준 페르소나 4 + 검증 웨이브)·운영 확인 결과를 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

조서희 님이 「통화 `call_id` → `customer_id` 조회」를 요청했다(재문의 고객 화면). `GET /hub/calls/{id}/record` 에 필드 하나 얹으면 된다 — 값은 HMAC 해시(원본 번호 아님).

## 완료 조건

- [ ] 응답 DTO 에 `customer_id` · 계약 테스트 · OpenAPI 반영
- [ ] 화면 쪽(조서희)에 필드명을 알린다

근거: 정성윤 11번 기록 「남은 것 ③」.
