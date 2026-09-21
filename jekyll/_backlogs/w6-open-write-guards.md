---
title: "열린 쓰기 둘 — /close 와 카드 피드백에 문이 없다"
assignee: "장민석"
role: "ai"
status: "todo"
sprint: 6
priority: 74
date: 2026-09-21
requirement:
  - "SEC-1"
paths:
  - "server/apps/hub/*"
---

## 무엇을

`POST /hub/calls/{id}/close` 와 **카드 피드백**이 **어느 토큰도 요구하지 않는다**([미결 항목](/open-items/) 09-21).
둘에 맞는 문을 단다.

## 지금 상태

`server/main.py` 주석은 「대시보드가 직접 부르는 쓰기는 사람 토큰(`require_agent`) 몫」이라 적지만
**실제로 걸린 것은 요약 확정·재수정뿐**이다(`postcall_router.py`·`card_feedback_router.py` 에 `require_agent` 0회).
서비스 토큰 문(`decisions/120`)도 이 둘은 비껴간다. `decisions/122` 가 *「토큰 만료보다 이쪽이 먼저」* 라고 적었다.

## ⚠ 카드 피드백에는 설계 제약이 있다

카드 피드백에 상담원 토큰을 그대로 걸면 안 된다는 제약이 [미결 항목](/open-items/)에 적혀 있다 — **먼저 그 항목을 읽는다.**
두 경로에 같은 문을 달 수 있는지부터가 판단 대상이다.

## 완료 조건

- [ ] 두 경로 각각 — 토큰 없음 401 · 틀린 토큰 401 · 맞는 토큰 200 테스트
- [ ] 프론트(`apps/call`)가 그 토큰을 실어 보내는지 조서희 님과 맞춘다 — **서버만 잠그면 화면이 깨진다**
- [ ] 읽기 경로(통화 목록·전사·기록) 무인증은 **이 티켓 범위 밖**임을 적고 미결에 그대로 둔다
