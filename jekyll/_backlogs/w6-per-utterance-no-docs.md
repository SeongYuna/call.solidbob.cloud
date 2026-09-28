---
title: "발화 줄마다 「관련 문서 없음」 — 추천 메시지의 segment_id 로만 표시"
assignee: "조서희"
role: "app"
status: "in-progress"
sprint: 6
priority: 62
date: 2026-09-28
requirement:
  - "B-6"
paths:
  - "apps/call/src/components/TranscriptPanel.tsx"
---
## 무엇을

`fired: true, cards: []`(B-6 관련 문서 없음)일 때 패널 전체 빈 문구만 있어 **어느 발화에서 못 찾았는지** 안 보였다(류준 인계 P1-5).
그 발화 줄 밑에 작게 「관련 문서 없음 — 이 발화로는 찾지 못했습니다」를 그린다.

## 막힌 것 — 콜 미디에이터 한 줄 (류준·정성윤)

추천 메시지(`recommendation`)에 **어느 세그먼트의 추천인지가 없다.** 서버 `RecommendResponse` 에도 없고,
`trigger_at_ms` 는 수신 시각(`received_at_ms`)이라 발화와 1:1 이 아니다. 화면에서 추정하면 엉뚱한 줄에 붙는다.

- 화면 쪽은 끝냈다 — 파서가 **선택 필드 `segment_id`** 를 읽고, 있을 때만 표시한다(없으면 아무것도 안 그린다).
- 필요한 것: `services/call-mediator/src/app/call_registry.ts` `recommend()` 의 방송 payload 에
  `segment_id: String(item.segmentId)` 추가 — `recommendation_pending` 이 이미 같은 키를 싣는다.
  `apps/` 밖이라 고치지 않았다.

## 완료 조건

- [x] 파서·스토어·렌더 테스트(`apps/call/test/p1Screens.test.tsx`)
- [ ] 콜 미디에이터가 `segment_id` 를 싣는다
- [ ] 운영에서 한 번 눈으로 확인
