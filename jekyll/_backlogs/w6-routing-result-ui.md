---
title: "배정 판정 결과를 화면에 보인다 — 지금은 미디에이터 로그만"
assignee: "조서희"
role: "app"
status: "in-progress"
sprint: 6
priority: 73
date: 2026-09-22
requirement:
  - "J-5"
paths:
  - "apps/admin/src/*"
  - "apps/call/src/*"
depends_on:
  - "w7-j5-routing-caller"
---
> **정성윤이 09-22 저녁 최종 QA(류준 페르소나 4 + 검증 웨이브)·운영 확인 결과를 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

J-5 배정 판정은 통화 시작 직후 미디에이터가 부른다(PR #131). 결과(`veteran` / 일반 배정 / 블랙리스트)는 로그와 `routing_log` 에만 있고 화면에 없다.
어디에 어떤 말로 보일지 장민석 님과 정한다 — 「배정 판정」으로 부르고, 연결을 바꾸지 못한다는 한계는 표시하지 않는다(`decisions/320`).

## 완료 조건

- [x] 표시 위치·문구 합의(관리자 통화 상세 또는 상담원 통화 시작 배너)
- [ ] `routing_log` 를 읽는 API 가 필요하면 장민석 님 티켓으로 쪼갠다
- [ ] 시연 SYN-006 → SYN-007 에서 `veteran` 이 화면에 보인다

근거: `w7-j5-routing-caller` 「남은 것 ②」.

## 2026-09-22 — 부분 착수 (조서희)

현황판(`admin-stats`) 집계 수치만 먼저 고쳤다 — 서버가 이미 주던
`routing_decisions`·`routing_blacklisted`·`routing_fell_back`을 `adminStore.ts`가
저장하지 않고 버리고 있었다(예전 "렌더하지 마라" 지시가 남긴 것 — 그때는 J-5
미구현이라 전부 0일 게 뻔했다). `WallboardTab.tsx`에 별도 섹션("배정 판정(J-5)")으로
추가, 기존 도넛 4지표에는 안 섞었다. 순수 프론트 변경이라 백엔드 대기 없이 바로 했다.

**나머지는 그대로 `todo`** — WS 실시간 배너(통화 중 표시)·상담기록 상세 필드·
`routing_log` 조회 API 는 전부 백엔드가 먼저 필요해 손대지 않았다. 완료 조건 3개
중 아직 하나도 체크 못 했다(집계 수치는 원래 조건에 없던 것을 추가로 고친 것).

## 2026-09-23 — WS 실시간 배너 완결 (조서희, 표시 위치는 09-22에 이미 정해 뒀다)

**표시 위치·문구는 사실 이미 정해져 있었다** — 09-22에 J-5 배선을 만들었다가 롤백할 때
(`w7-j5-routing-caller` 참고) `apps/call`의 WS 파싱·스토어(`routingDecision`)·
`TranscriptPanel.tsx` 배너("배정 판정 기록됨 · 블랙리스트 여부 · 일반 배정 사유")는
안 지웠다 — 백엔드가 그 메시지를 안 보내서 잠들어 있었을 뿐이다. 1번 조건은 그래서
체크만 늦었다.

**진짜 빠진 건 방송 자체였다.** `services/call-mediator`의 `decideRouting()`은 판정을
부르고 **로그에만** 남기고 있었다(`call_registry.ts` 옛 주석: "화면 표시는 조서희 님과
정한 뒤다"). `w6-close-callid-missing`에서 쓴 것과 같은 패턴으로 고쳤다:

- `ports.ts`에 `CallMediatorMessage`에 `routing_decision` 추가(`RoutingDecisionPayload`는
  이미 있었다)
- `call_registry.ts`의 `RegistryDeps.announceRouting`(기본 false) 신설, `decideRouting()`
  성공 시 서버 응답을 그대로 방송(변형 없음 — 서버 `routing_decision_schema.py`가 프론트
  `parseRoutingDecision`이 요구하는 필드를 전부 갖고 있는 것을 확인했다)
- `main.ts`에서 `announceRouting: true`로 켰다
- 테스트 3건(꺼져있으면 안 보냄·켜져있으면 그대로 방송·판정 실패면 안 보냄) —
  `npm test` 163/163

**남은 것** — 운영 재확인(SYN-006 → SYN-007에서 실제로 `veteran` 배너가 뜨는지, 3번
조건)과 `routing_log` 조회 API(2번 조건, 필요하면 장민석 님 티켓)는 그대로 `todo`다.
`status`는 `in-progress`로 유지한다.
