---
title: "블랙리스트 문장 보존 정리 — 끝난 뒤 180일"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 4
priority: 19
date: 2026-09-15
requirement:
  - "J-4"
  - "SEC-1"
paths:
  - "server/apps/blacklist/domain/services/retention.py"
  - "server/apps/hub/adapter/inbound/api/v1/blacklist_retention_purge_router.py"
---

## 무엇을

`decisions/205` ⑤ 「반려 요청 사유를 일정 기간 뒤 비운다」 와 `decisions/309` 만료 변경 사유 보존이 미정이었다. 끝난 뒤 180일, 관리자 API 로 비운다(`decisions/312`, 사용자 선택).

## 완료 조건

- [x] 도메인 규칙 2 · 라우터(401·200) · 리포지토리 integration 1(400일 전 끝난 것만 비움 · 진행 중·최근 반려·승인 요청은 남김 · 멱등)
- [x] 스키마 변경 없음 — 행을 지우지 않고 표시로 바꾼다
- [ ] 누가 언제 부를지(주기 실행) — [미결](/open-items/)
