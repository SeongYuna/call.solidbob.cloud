---
title: "D-2 문의 유형이 24/24 NULL — `/close` 가 요약은 저장하는데 `inquiry_type` 을 비운다"
assignee: "장민석"
role: "ai"
status: "todo"
sprint: 6
priority: 67
date: 2026-09-22
requirement:
  - "D-2"
paths:
  - "server/apps/postcall/*"
  - "server/apps/hub/*"
---
> **정성윤이 09-22 저녁 최종 QA(류준 페르소나 4 + 검증 웨이브)·운영 확인 결과를 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

09-22 E2E 24건 전부 `call.inquiry_type` 이 NULL 이다. `/close` 는 요약을 저장하지만 유형 분류 결과를 쓰지 않는다(판정기는 요약 길이만 봐서 못 잡았다).

## 완료 조건

- [ ] `/close` 가 D-2 분류 결과를 `inquiry_type` 에 저장 · 분류 실패면 NULL 이 아니라 「미분류」 값
- [ ] 계약 테스트 1건 · `e2e_check.py` 가 NULL 을 ❌ 로

근거: 미결 「D-2 문의 유형」.
