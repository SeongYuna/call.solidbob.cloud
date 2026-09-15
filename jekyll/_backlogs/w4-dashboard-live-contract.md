---
title: "대시보드를 실서버에 붙인다 — mock 위에서만 도는 화면들"
assignee: "조서희"
role: "app"
status: "todo"
sprint: 4
priority: 45
date: 2026-09-15
requirement:
  - "A-1"
  - "B-4"
paths:
  - "apps/call/src/*"
---

## 무엇을

2026-09-14 에 **백엔드가 먼저 나간** 기능들의 프론트 연결을 끝낸다.
[미결 항목](/open-items/) 「조서희 님께 — 대시보드가 받아야 할 서버·게이트웨이 계약(2026-09-14)」이 원본이다.

## 붙일 것 넷

- [ ] **「검색 중」 신호 수신** — 게이트웨이가 추천 요청 직전에 `recommendation_pending` 을 쏜다
      ([w4-recommendation-pending-contract](/backlog/w4-recommendation-pending-contract/)).
      ⚠ **지금 게이트웨이 쪽은 코드만 있고 꺼 둔 상태**다 — 프론트가 받을 준비가 되면 켠다
- [ ] **통화 목록**(`GET /hub/calls`) — 재상담 이력 카드가 지금 mock 위에서 돈다
- [ ] **블랙리스트**(J) — 서버 어댑터·라우터는 09-14 에 생겼다([w4-blacklist-api](/backlog/w4-blacklist-api/)).
      화면은 아직 mock 이다
- [ ] **F-2 필요서류 체크리스트** — `decisions/305` 로 다산 규칙표가 들어왔다

## 왜 지금

**「배포됐다」와 「화면에 뜬다」가 다르다.** 09-14 에 관리자 로그인이 배포됐는데 운영에선 500 이었고
`/health` 는 `ok` 였다([w4-admin-auth-runtime](/backlog/w4-admin-auth-runtime/)) — **눌러 보기 전에는 모른다.**
같은 모양이 이 넷에도 있다.

## 완료 조건

네 기능이 **mock 을 끄고도** 라이브 모드에서 동작하고, 안 되는 것은 «안 된다» 로 화면에 드러난다
(조용히 빈 목록을 보여주지 않는다).
