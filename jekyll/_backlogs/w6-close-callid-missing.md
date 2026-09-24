---
title: "미발동 추천의 `call_id` 누락으로 `callId` 가 빈 문자열 → `/close` 404 — 요약·확정·블랙리스트 요청이 사라진다"
assignee: "조서희"
role: "app"
status: "in-progress"
sprint: 6
priority: 59
date: 2026-09-22
paths:
  - "apps/call/src/*"
  - "services/call-mediator/src/*"
---
> **정성윤이 09-22 저녁 최종 QA(류준 페르소나 4 + 검증 웨이브)·운영 확인 결과를 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

09-22 최종 QA: 추천이 발동하지 않은 통화에서 `call_id` 가 안 실려 `callId` 가 `""` 가 되고, 통화 종료 `/close` 가 404 로 끝난다.
그러면 요약·확정·블랙리스트 요청이 전부 사라진다. `apps/call/src/lib/realCallMediatorClient.ts:384`.

## 왜

시연 한 통을 끝까지 돌리는 조건 4 의 직접 걸림돌이다. 추천이 안 뜬 통화(맞장구만 있는 짧은 통화)에서 반드시 난다.

## 완료 조건

- [x] `callId` 를 추천이 아니라 통화 시작 메시지(`started`)에서 잡는다
- [ ] 추천 0건 통화로 `/close` 200 · 요약 저장 확인(파서 테스트 1건)

근거: 미결 「대시보드 — 조서희」 ①.

## 2026-09-23 — 원인 정정 + 구현 (조서희)

**원인 문구를 고쳤다.** `callId`는 `applyTranscript`·`applyRecommendation`·`applyClosure`
셋 중 아무거나 한 번 오면 잡힌다(같은 `set()` 호출 안에서 `utterances`와 함께 채워진다) —
"추천이 없어서"가 아니라 **전사·추천·판정 중 아무 이벤트도 안 온 통화**(맞장구조차 STT에
안 잡힌 아주 짧은 통화)가 정확한 조건이다.

**진짜 원인은 §7.3 계약에 "통화 시작" 메시지 자체가 없던 것** — `services/call-mediator`가
보내는 메시지 종류(`ports.ts`)에 `started`가 없어 프론트가 잡을 수 있는 가장 이른 신호가
"첫 발화"뿐이었다. 그래서 `apps/call`만으로는 완결이 안 됐다:

- `services/call-mediator`: `ports.ts`에 `StartedPayload`(`{call_id}`)·`CallMediatorMessage`에
  `started` 추가. `RegistryDeps.announceStarted`(기본 false, 다른 `announce*`와 같은 안전장치)
  추가. `call_registry.ts`의 `callFor()` — 서버 `POST /hub/calls` 성공 직후(통화당 한 번,
  화자 둘이어도 한 번) `broadcaster.publish(callId, {type: "started", ...})`. `main.ts`에서
  `announceStarted: true`로 켰다(프론트 파서가 같은 커밋에 들어간다). 테스트 3건 추가
  (꺼져있으면 안 보냄·화자 둘이어도 한 번·시작 실패면 안 보냄) — `npm test` 160/160.
- `apps/call`: `CallMediatorListener.onStarted?` 신설, `realCallMediatorClient.ts`에
  `started` 파싱 추가, `useCallMediatorSession.ts`에서 `callStore.applyStarted(callId)`로
  연결. `applyStarted`는 `callId`만 세팅하고 `utterances`는 건드리지 않는다(세그먼트가
  없으므로). mock은 그대로 둔다 — mock 시나리오는 이미 callId를 안다.
- **안전장치도 남겼다** — `useCallMediatorSession.wrapUp()`이 `callId`가 비어 있으면
  `/close`를 아예 안 부르고 "통화 번호를 아직 받지 못했습니다…" 오류로 바꾼다. `started`
  메시지가 와야 할 통화에서 무슨 이유로든 안 왔을 때(연결 끊김 등) 빈 문자열로 404 나던
  것 대신 원인이 보이는 오류가 뜬다.

**남은 것 — 완료 조건 2번, 검증 못 함**: `apps/call`엔 테스트 실행기 자체가 없다(`package.json`에
test 스크립트 없음, `test/` 디렉터리도 없음) — "파서 테스트 1건"을 추가할 인프라가 없다.
빌드·타입체크(`tsc --noEmit`·`vite build`)만 통과 확인했고, **실제로 추천 0건 통화를 운영에서
끝까지 돌려 `/close` 200을 본 적은 없다.** 그래서 `status`를 `done`이 아니라 `in-progress`로
둔다 — 코드는 됐지만 실측이 없다(절대 원칙 2).
