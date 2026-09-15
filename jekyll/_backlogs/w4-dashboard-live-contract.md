---
title: "대시보드를 실서버에 붙인다 — mock 위에서만 도는 화면들"
assignee: "조서희"
role: "app"
status: "in-progress"
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

- [x] **「검색 중」 신호 수신** — 게이트웨이가 추천 요청 직전에 `recommendation_pending` 을 쏜다
      ([w4-recommendation-pending-contract](/backlog/w4-recommendation-pending-contract/)).
      2026-09-15 `realGatewayClient.ts`에 파싱 추가(`call_guard`도 같이). ⚠ 게이트웨이 쪽은
      여전히 꺼 둔 상태라 실제로 켜지기 전까지는 라이브 트래픽으로 확인 못 했다
- [ ] **통화 목록**(`GET /hub/calls`) — REST 함수(`coreClient.ts`)는 만들었으나 재상담 이력
      화면(`CallHistoryPanel`·`CallSummaryPanel`)은 여전히 mock 시나리오 위에서 돈다.
      실제 API는 통화 목록+자막만 주고 카드·종결·감정분석 재생 데이터가 없어, 화면을
      그대로 바꿔 끼우면 재생 기능이 빠진다 — 제품 판단(재생 기능 범위 축소를 받아들일지)이
      먼저 필요해서 미룸
- [x] **블랙리스트**(J) — 서버 어댑터·라우터는 09-14 에 생겼다([w4-blacklist-api](/backlog/w4-blacklist-api/)).
      2026-09-15에 실제로 붙였다 — `apps/call`은 `POST /hub/blacklist-requests` 로 요청 생성,
      `apps/admin`은 `GET/POST /hub/blacklist-requests(/decision)`·`GET/POST
      /hub/blacklist-entries(/release)`를 로그인 직후 실제로 부른다
- [x] **F-2 필요서류 체크리스트** — `decisions/305` 로 다산 규칙표가 들어왔다. 2026-09-15에
      프론트 계약(`ClosureEvent`)을 그 형식(`procedure`·`verdict complete/incomplete`·
      `detected`·`conditional`)에 맞췄다 — 게이트웨이가 새 형식 전송을 켜면 바로 받는다

## 왜 지금

**「배포됐다」와 「화면에 뜬다」가 다르다.** 09-14 에 관리자 로그인이 배포됐는데 운영에선 500 이었고
`/health` 는 `ok` 였다([w4-admin-auth-runtime](/backlog/w4-admin-auth-runtime/)) — **눌러 보기 전에는 모른다.**
같은 모양이 이 넷에도 있다.

## 완료 조건

네 기능이 **mock 을 끄고도** 라이브 모드에서 동작하고, 안 되는 것은 «안 된다» 로 화면에 드러난다
(조용히 빈 목록을 보여주지 않는다). **2026-09-15 진행 상황**: 블랙리스트·F-2 계약·검색 중 신호
셋은 붙였다(라이브 게이트웨이로 아직 실측은 못 함). 통화 목록만 남았고, 그 과정에서 계약
불일치 두 건을 추가로 발견했다 — **카드 피드백**(`POST /hub/cards/{id}/feedback`)은 추천
카드 응답에 `card_id`가 없어 호출할 수 없고, **관리자 지식베이스 갭 화면**은 mock
집계(`{query, found}`)와 실제 계약(`{module, description, status}`)의 모양이 달라 다시
설계해야 한다. 둘 다 이 티켓 범위 밖이라 새로 등록이 필요하다.
