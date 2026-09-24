---
title: "읽기 경로에 인증이 걸리면 화면이 토큰을 싣는다 — `w6-read-path-auth` 와 같은 릴리스"
assignee: "조서희"
role: "app"
status: "done"
sprint: 6
priority: 69
date: 2026-09-22
requirement:
  - "SEC-1"
paths:
  - "apps/call/src/*"
  - "apps/admin/src/*"
depends_on:
  - "w6-read-path-auth"
---
> **정성윤이 09-22 저녁 최종 QA(류준 페르소나 4 + 검증 웨이브)·운영 확인 결과를 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

통화 목록·전사·기록·검색 조회에 문이 걸리면(`w6-read-path-auth`, 장민석) 상담원 화면·관리자 화면이 그 호출에 토큰을 실어야 한다.
먼저 걸면 화면이 깨지고, 화면만 먼저 하면 의미가 없다 — **같은 날 같은 릴리스**로 맞춘다.

## 완료 조건

- [x] 장민석 님 라우터 표에 있는 GET 마다 `authedGet` 패턴 적용
- [ ] 운영에서 토큰 없는 탭(로그아웃)에서 목록이 비고 오류 문구가 뜬다

## 2026-09-23 — 구현 (조서희)

착수 전에 `w6-read-path-auth`를 다시 확인하니 **막혀 있지 않았다** — 장민석이 "같은
릴리스" 대신 2단계로 갔고(`decisions/322`), 서버는 이미 `0.1.35`로 배포돼 있다(`read_guard: open`
— 토큰 없이 보내도 지나가는 과도기). "남은 것: 그 한 줄(`READ_AUTH_REQUIRED=true`)"이
프론트가 토큰을 싣는 걸 기다리고 있었다.

`coreClient.ts`에 `agentAuthHeaders()`(상담원 토큰이 있으면 `Authorization: Bearer`,
없으면 헤더 없이 그대로 — 과도기 호환, `closeCall`류처럼 없다고 던지지 않는다) 신설,
결정 322의 라우터 표 그대로 넷에 붙였다: `fetchCallList`(GET /hub/calls)·
`fetchCallTranscript`·`fetchCallRecord`·`searchDocuments`(POST /hub/search). 지식 공백
신고(`POST /hub/knowledge-gaps`)는 `apps/call`에 부르는 화면이 아직 없어(결정 322에도
"부르는 곳이 없다") 범위 밖이다. `apps/admin`은 이미 관리자 토큰을 싣고 있어 손대지
않았다.

완료 조건 2번은 기존 코드로 이미 뒷받침돼 있다 — `CallHistoryPanel.tsx`·
`callStore.openHistory` 둘 다 `try/catch`로 실패 시 오류 문구를 보여주는 구조라, 토큰이
붙었으니 서버가 잠기면(`READ_AUTH_REQUIRED=true`) 로그아웃 탭은 자연히 그 경로를 탄다
— 다만 **실제로 잠긴 뒤 눌러 확인한 적은 없다.**

검증: `tsc --noEmit`·`vite build`·`npm test`(11/11) 통과. 운영에서 실측은 못 했지만
프론트 몫(완료 조건 1번)은 끝났고, **서버 쪽에 "붙었다"고 알렸다** — `w6-read-path-auth`에
남긴 것을 참고. `done`으로 올린다.
