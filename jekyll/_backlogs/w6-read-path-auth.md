---
title: "읽기 경로 인증 — 통화 목록·전사·기록·검색이 무인증이고 지식 공백 설명이 마스킹 없이 저장된다"
assignee: "장민석"
role: "ai"
status: "todo"
sprint: 6
priority: 58
date: 2026-09-22
requirement:
  - "SEC-1"
paths:
  - "server/apps/hub/*"
---
> **정성윤이 09-22 저녁 최종 QA(류준 페르소나 4 + 검증 웨이브)·운영 확인 결과를 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

운영에서 토큰 없이 열린다(09-22 최종 QA 실측): `GET /hub/calls`(12건 · 실제 음성 테스트 통화 포함 · 고객 HMAC · `?customer_id=` 필터) ·
`/transcript` · `/record` · `GET/POST/PATCH /hub/knowledge-gaps`(**설명이 마스킹 없이 저장**) · `POST /hub/search`.
쓰기 경로는 09-22 fail-closed 로 닫혔다(PR #131). **09-30 전에 닫히지 않은 가장 큰 구멍**이다.

## 어떻게

1. 라우터 표(경로 · 지금 문 · 걸 문 — 상담원 토큰 / 서비스 토큰 / 관리자 세션)를 결정 기록 `3xx` 로
2. `knowledge-gaps` 설명은 저장 전에 마스킹 스포크를 태운다(SEC-1)
3. 화면이 토큰을 싣는 것(`w6-read-path-token-ui`, 조서희)과 **같은 릴리스**에 — 먼저 걸면 화면이 깨진다

## 완료 조건

- [ ] 결정 기록 + 라우터 표
- [ ] 토큰 없는 GET 이 401 인 테스트(경로마다)
- [ ] `knowledge-gaps` 저장본에 원문이 없는 테스트

근거: 미결 「읽기 경로 인증 없음」 · 마감 체크리스트 13번.
