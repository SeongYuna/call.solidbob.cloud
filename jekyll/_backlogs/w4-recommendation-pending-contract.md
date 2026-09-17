---
title: "「검색 중」 신호 recommendation_pending + 통화 시작 — §7.3 계약 반영"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 4
priority: 5
date: 2026-09-14
requirement:
  - "A-3"
  - "B-1"
paths:
  - "services/call-mediator/src/app/call_registry.ts"
  - "_project/plan.md"
---

## 무엇을

- **통화 시작** — 콜 미디에이터가 첫 채널을 열 때 `POST /hub/calls` 를 이미 부른다(`decisions/301`). §7.3 계약에만 없다
- **검색 중 신호** — 대시보드 mock 은 `onRecommendationPending` 으로 로딩 UI 를 띄우는데 실서버 경로에는 신호가 없다
  ([미결](/open-items/) 2026-09-09). 콜 미디에이터가 추천을 부르기 직전 `{"type":"recommendation_pending"}` 을 보낸다

## ⚠ 전송은 꺼 둔다

지금 `apps/call` 의 `realCallMediatorClient.ts` 는 **모르는 `type` 에 오류 배너**를 띄운다. 켜면 라이브 화면이 깨지므로
콜 미디에이터에는 코드만 넣고 기본값은 끈다. `apps/` 는 조서희 님 전담이라 여기서 고치지 않는다 — 수신 코드가 들어가면 켠다.

## 완료 조건

- [x] `plan.md` §7.3 에 통화 시작·검색 중 메시지 추가
- [x] 콜 미디에이터 `announcePending` (기본 false) + 테스트
- [x] 조서희 님께 요청을 미결 항목에 남긴다
