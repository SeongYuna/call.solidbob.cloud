---
title: "프론트 테스트 도입 — vitest · WS 파서 4종부터"
assignee: "조서희"
role: "app"
status: "done"
sprint: 6
priority: 78
date: 2026-09-22
requirement:
  - "QUA-1"
paths:
  - "apps/call/src/*"
---
> **정성윤이 09-22 저녁 최종 QA(류준 페르소나 4 + 검증 웨이브)·운영 확인 결과를 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

프론트 테스트가 0 이다(09-22 최종 QA 「테스트·CI 위생」). `apps/call` 의 WS 파서(자막 · 추천 · 컴플라이언스 · 종료)는 서버 필드명이 바뀌면 조용히 깨지는 곳이라 여기부터.

## 완료 조건

- [x] `vitest` 설정 · 파서 4종 테스트(실제 방송 JSON 표본으로)
- [x] `npm test` 가 `package.json` 에 있다 — CI 잡·룰셋 추가는 정성윤(`test.yml` job + `ruleset-main.json`)

근거: `rfp-harness.md` QUA-1.

## 2026-09-23 — 구현 (조서희)

`vitest ^5.0.1` devDependency 추가, `package.json`에 `"test": "vitest run"`. 설정 파일은
안 만들었다 — 순수 함수(파서) 테스트라 jsdom 등 특별한 환경이 필요 없어 vitest 기본값으로
충분했다.

`apps/call/test/realCallMediatorClient.test.ts` — 요청한 4종(자막·추천·컴플라이언스·종료)에
오늘 새로 생긴 `started`(`w6-close-callid-missing`)까지 5종, **11개 테스트**:

- 표본은 실제 서버 응답 모양을 그대로 썼다 — §7.3 계약대로 숫자·불린도 문자열("true"·"1500")로
  넣고 파서가 숫자·불린으로 바꾸는지 검증한다. 출처는
  `services/call-mediator/test/ws_server.test.ts`(실측 방송 검증)와 `ports.ts` 타입.
  자막·컴플라이언스·종료는 오늘 이 세션에서 실제로 고친 코드 경로라 회귀 보호 가치가 크다.
  - 각 파서마다 "제대로 된 표본"과 "계약을 어긴 표본"(불린이 문자열이 아님·verdict가
    옛 `approved`/`blocked`·findings가 배열이 아님) 한 쌍 — 조용히 깨지지 않고 `null`을
    돌려주는지 확인
  - `parseCallMediatorMessage`가 모르는 타입·문자열·`null`을 받았을 때도 확인

**CI 잡·룰셋 추가는 안 했다** — 티켓이 애초에 정성윤 몫으로 갈라 뒀다(`test.yml`에 `call`
job 신설 + `ruleset-main.json`에 필수 검사 추가). `npm test` 통과(11/11)·`npm run build`
클린은 확인했다.
