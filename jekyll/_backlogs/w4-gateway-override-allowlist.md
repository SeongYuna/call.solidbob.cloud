---
title: "?gateway= 런타임 오버라이드에 허용 목록 + 배너 추가"
assignee: "조서희"
role: "app"
status: "done"
sprint: 4
priority: 1
date: 2026-09-14
paths:
  - "apps/call/src/lib/ws/types.ts"
  - "apps/call/src/components/GatewayOverrideBanner.tsx"
---

무엇: `apps/call/src/lib/ws/types.ts`의 `?gateway=` 런타임 오버라이드가 `ws://`·`wss://`로
시작하기만 하면 아무 주소나 localStorage에 저장하던 것을 허용 목록으로 막고, 켜져 있는 동안
화면에 배너를 띄운다.

왜: `jekyll/open-items.markdown`(2026-09-11 항목)이 이미 지적한 실제 보안 구멍이다.
`call.solidbob.cloud/?gateway=wss://<공격자 서버>/ws` 링크 하나로 상담원 브라우저를 다른
서버에 붙여, 그 서버가 보내는 가짜 자막·가짜 "필요서류" 카드를 실제 응답인 것처럼 띄울 수
있었다 — 운영 번들에 이미 떠 있는 상태였다.

완료 조건:
- [x] `isAllowedGatewayUrl()` — `wss://server.solidbob.cloud/gateway/*`와
      `ws://localhost`·`ws://127.0.0.1`(로컬 개발)만 통과, 나머지는 조용히 버림
      (서브도메인 스푸핑 케이스 `server.solidbob.cloud.evil.com`도 확인)
- [x] `GatewayOverrideBanner.tsx` — 오버라이드 활성 중 화면 상단에 주소 + 「연결 해제」 버튼
- [x] `cd apps/call && npm run typecheck && npm run build` 통과
- [x] `jekyll/open-items.markdown` 해당 항목 [x]로 갱신

근거: `jekyll/open-items.markdown` "⚠ `?gateway=` 가 아무 WebSocket 주소나 받아 저장한다" 항목
(2026-09-11 신규, 정성윤이 조서희에게 남김). 사용자 지시로 진행(2026-09-14).
