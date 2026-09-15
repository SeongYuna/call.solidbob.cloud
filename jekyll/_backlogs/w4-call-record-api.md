---
title: "통화 기록 조회 GET /hub/calls/{id}/record — 상담기록 재생"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 4
priority: 14
date: 2026-09-15
requirement:
  - "B-5"
  - "D-1"
  - "F-2"
paths:
  - "server/apps/hub/adapter/outbound/postgres/call_record_repository.py"
  - "server/apps/hub/adapter/inbound/api/v1/call_record_router.py"
---

## 무엇을

상담기록 재생 화면이 mock 이었다 — 서버에 통화 목록·자막만 있고 **그 통화의 카드·필요서류 판정·요약을 다시 읽는 API 가 없었다.**
셋 다 이미 저장되고 있어(추천은 `decisions/308` 부터) 조회만 붙였다.

## 완료 조건

- [x] 인터랙터 3 · 라우터 3 · 리포지토리 integration 1(저장 어댑터 셋이 남긴 것을 한 번에 읽는다)
- [x] 실제 앱 + postgres:17: 없는 통화 404 · 요약·카드 `card_id`·판정 서류 항목까지
- [ ] 운영 반영 · 프론트 연결(조서희) — 감정분석은 저장되지 않아 없다
