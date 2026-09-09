---
title: "fired 필드 계약 반영 + e2e_latency_ms 를 로딩 UI로 대체"
assignee: "조서희"
role: "app"
status: "done"
sprint: 3
priority: 6
date: 2026-09-09
paths:
  - "apps/dashboard/src/types/contract.ts"
  - "apps/dashboard/src/lib/ws/realGatewayClient.ts"
  - "apps/dashboard/src/store/callStore.ts"
  - "apps/dashboard/src/components/TermsPanel.tsx"
---

## 무엇을

서버 `RecommendResponse.fired`(필수 필드)가 프론트 `RecommendationBatch` 타입에 없어서
"검색 안 함"(`fired:false`)과 "검색했으나 결과 없음"(`fired:true, cards:[]`, B-6)을
화면에서 구분하지 못하던 문제를 고쳤다. 함께, 안 쓰던 `e2e_latency_ms` 필드를 지우고
카드 응답을 기다리는 동안 로딩 인디케이터를 보여주도록 바꿨다.

## 왜

`_project/decisions/401` 참고 — 서버는 처음부터 이 구분을 보내고 있었는데(`w3-recommendation-pipeline`)
프론트 타입 쪽에서 누락돼 있었다. `e2e_latency_ms`는 화면 어디에도 실제로 쓰이지 않는
죽은 필드였다.

## 완료 조건

- [x] `RecommendationBatch.fired: boolean` 추가, `e2e_latency_ms` 제거
- [x] `realGatewayClient.ts` 파서가 `fired:false` 서버 응답(필드 대부분 없음)을 그대로 받는다
- [x] 스토어에 `cardsLoading`/`lastFired` 추가, `TermsPanel` 팝업뷰가 세 상태 + 로딩을 구분해 보여준다
- [x] mock 게이트웨이가 트리거 시점에 로딩 신호를 먼저 보내고 `internal_latency_ms` 뒤 카드를 배달
- [x] `npm run typecheck` 통과

## 남은 것

- **로딩 신호(`onRecommendationPending`)는 §7.3 계약에 없다 — mock 전용이다.** 실서버 연동 시
  게이트웨이가 이 신호를 보내도록 계약에 추가하지 않으면 라이브 모드에서는 로딩 UI가 뜨지 않는다.
- 브라우저 육안 확인 미완 — 이 환경에 Chrome 자동화가 없어 파서·스토어 로직만 스크립트로 검증했다.
