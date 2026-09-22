---
title: "관리자 현황판을 GET /hub/admin-stats 하나로 채운다"
assignee: "조서희"
role: "app"
status: "todo"
sprint: 6
priority: 60
date: 2026-09-22
requirement:
  - "J-3"
  - "D-4"
depends_on:
  - "w6-admin-stats-api"
paths:
  - "apps/admin/src/components/admin/WallboardTab.tsx"
  - "apps/admin/src/lib/api/hubClient.ts"
---

> **정성윤이 09-22 오늘 진행 기록·미결 항목을 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

장민석 님이 09-22 에 만든 `GET /hub/admin-stats`([w6-admin-stats-api](/backlog/w6-admin-stats-api/))로 관리자 현황판 숫자를 채운다.
관리자 토큰으로 부르면 여덟 칸(통화 전체·종료·콜 가드·승인 대기·활성 등록·배정 판정 셋)이 **문자열**로 온다. 지금 현황판은 mock 시드다.

## 지킬 것

- 상담원 단위로 쪼개지 않는다(부록 A-1)
- 표본이 0 이면 숫자 0 이 아니라 **「표본 없음」** · 온도 이상 `null` 은 「미측정」
- 「완료 통화 누적」을 `calls_total` 과 `calls_closed` 중 무엇으로 보일지 정해 적는다

## 완료 조건

- [ ] 현황판 숫자가 mock 이 아니다 — 운영에서 오늘 합성 통화 4건이 보인다
- [ ] 로그인 풀림(401)은 별도 문구
