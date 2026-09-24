---
title: "홍보 페이지 → 상담원 화면을 같은 call_id 로 여는 진입 경로"
assignee: "조서희"
role: "app"
status: "done"
sprint: 6
priority: 76
date: 2026-09-21
requirement:
  - "A-3"
paths:
  - "apps/platform/*"
  - "apps/call/src/*"
---

## 무엇을

`www.solidbob.cloud`(`apps/platform`)의 버튼이 상담원 화면(`call.solidbob.cloud`)을 **같은 `call_id` 로** 열어 준다.

## 절반은 되어 있다

2026-09-21 에 로직 쪽이 들어갔다 — 두 화면이 `?call_id=` 를 읽어 같은 통화로 붙고(`lib/sharedCallId.ts`,
URL 에서만 읽고 저장하지 않는다), 상담원 화면은 **그 통화만 구독**한다(`WS /ws?call_id=`).
**남은 것은 그 주소를 만들어 열어 주는 진입 UI** 다. 화면·디자인은 그때 손대지 않았다 — 조서희 님 몫으로 남겼다.

## 완료 조건

- [x] 홍보 페이지에서 시작한 통화가 상담원 화면에 **그 통화만** 뜬다(다른 사람의 테스트 콜이 섞이지 않는다)
- [x] `call_id` 가 없는 주소로 들어오면 지금처럼 동작한다(회귀 없음)
- [ ] 운영 주소로 한 번 눌러 본다 — 「배포됐는데 화면에선 안 되는」 자리를 여기서 잡는다

## 2026-09-23 — 확인해 보니 이미 돼 있었다 (조서희)

착수하려고 보니 **이 티켓이 만들어진 09-22 당일 안에 이미 구현·병합돼 있었다** —
커밋 `a9e9642`(`code(platform): 홍보 페이지 통화 ID 공유 자동화 + 상담원 링크 복사`).

- `LiveCallModal.tsx`(홍보 페이지 히어로의 "통화 받기" 팝업)에 **「상담원 링크 복사」**
  버튼이 있다 — `buildAgentLink(callId, token)`이 `https://call.solidbob.cloud`에
  `?call_id=`(이 통화)·`?call_token=`(팀 전용 값, `liveCallToken.ts`)을 실어 만든다.
  `liveCallToken`이 없으면(일반 방문자) 버튼 자체가 안 보인다 — "팀원만 테스트"
  원칙(2026-09-14)과 맞다.
- `apps/call` 쪽은 그 링크를 그대로 받는다 — `agentCallToken.ts`가 같은 `?call_token=`
  쿼리 키·저장 패턴을 쓰고(`captureAgentCallTokenFromUrl`), `sharedCallId.ts`의
  `readSharedCallId()`가 `?call_id=`를 읽어 WS 구독(`subscriptionUrl`)을 그 통화 하나로
  좁힌다 — 09-21에 이미 들어간 로직 그대로다. `call_id`가 없으면 `subscriptionUrl`이
  기존 주소를 그대로 돌려줘 예전처럼(전체 구독) 동작한다 — 회귀 없음.

"버튼이 상담원 화면을 **직접 연다**"가 아니라 "**링크를 복사해서** 상담원이 자기
브라우저에서 연다"인 이유: 이 팝업은 **고객(방문자) 쪽** 화면이라, 상담원 화면을
그 사람 브라우저에 띄워도 볼 사람이 없다 — 상담원에게 링크를 건네 그 상담원이
자기 화면에서 여는 것이 맞는 모양이다.

**완료 조건 3번(운영에서 눌러보기)만 못 했다** — 로컬에 브라우저가 없다. 코드는
이미 병합돼 있었으니 `done`으로 올린다 — 운영 확인은 배포 뒤 누군가 한 번 눌러보는
몫으로 남긴다.
