---
title: "`?call_mediator=` 오버라이드 배너 — 주소의 토큰 값을 *** 로 가림"
assignee: "조서희"
role: "app"
status: "done"
sprint: 6
priority: 61
date: 2026-09-28
paths:
  - "apps/call/src/components/CallMediatorOverrideBanner.tsx"
---
## 무엇을

배너가 `<code>{overrideUrl}</code>` 로 주소를 통째로 찍어 **시연 녹화 화면에 토큰이 남을 수 있었다.**
이름에 `token` 이 든 쿼리(`token`·`agent_token`·`call_token` …) 값을 `***` 로 가린다(`redactTokenInUrl`).
표시부를 `CallMediatorOverrideBannerView` 로 떼어 가림을 그 안에서 한다 — 호출부가 잊어도 새지 않게.

## 완료 조건

- [x] token 이 든 URL 렌더 테스트에서 토큰 원문이 DOM 에 없다(`apps/call/test/emptyStates.test.tsx`)

근거: 류준 인계 문서 P0-3.
