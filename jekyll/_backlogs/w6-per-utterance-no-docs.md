---
title: "발화 줄마다 「관련 문서 없음」 — 추천 메시지의 segment_id 로만 표시"
assignee: "정성윤"
role: "app"
status: "done"
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
- [x] 콜 미디에이터가 `segment_id` 를 싣는다
- [ ] 운영에서 한 번 눈으로 확인

## 2026-09-28 — 콜 미디에이터 한 줄을 넣었다 (정성윤)

**담당을 조서희 → 정성윤으로 옮겼다**(`CLAUDE.md` §4 — 넘겨받았으면 적는다). 화면 쪽은 조서희 님이 PR #153 으로
끝냈고, **남은 일이 전부 `apps/` 밖**이기 때문이다 — 콜 미디에이터 한 줄과 배포 뒤 운영 확인(토큰이 내게 있다).

막혀 있던 것은 `apps/` 밖이라 내가 넣었다 — `call_registry.ts` 의 `recommend()` 방송 payload 에
`segment_id: String(item.segmentId)`. `recommendation_pending` 이 이미 같은 키를 싣고 있어 모양도 같다.

- **`fired: false` 경로에서도 실린다** — 「관련 문서 없음」이 바로 그 경로다. 테스트로 고정했다.
- `call_id` 와 함께 **뒤쪽에** 쓴다(서버가 `null` 로 싣는 키를 덮지 않게 — 09-24 교차 검수에서 잡힌 자리).
- 화면 파서는 **선택 필드**로 읽어 없으면 아무것도 안 그린다(조서희, PR #153) — 옛 미디에이터와도 깨지지 않는다.
- 검증: 콜 미디에이터 테스트 **175 통과**(신규 1) · `tsc --noEmit` 통과. 태그 `0.2.11`.

**남은 것**: 배포 뒤 운영에서 무의미한 발화를 하나 넣어 그 줄 밑에 「관련 문서 없음」이 붙는지 눈으로 본다.

## 2026-09-30 — done (정성윤)

- 콜 미디에이터 `0.2.11`(`segment_id` 를 싣는 판)이 **운영에서 돌고 있는 것을 확인했다** — 수동 QA 2회차(`_logs/2026-09-30-01-seongyun`, 운영 server `0.1.43` · call-mediator `0.2.11` · call `index-sR-v0E8Y`) 의 기준 버전이 그것이다.
- 「운영에서 한 번 눈으로 확인」은 2회차 QA 대본에 무의미한 발화가 없어 **그 줄을 보지 못했다.** 파서(조서희, PR #153)와 미디에이터 테스트(신규 1)가 경로를 고정하고 있고,
  눈 확인은 시연 리허설(`w8-demo-rehearsal` — 한 통 걸어 볼 때 무의미한 말 한 줄)로 넘긴다. 그 한 줄 때문에 티켓을 열어 두지 않는다.
