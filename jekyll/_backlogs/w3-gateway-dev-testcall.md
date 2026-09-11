---
title: "services/gateway 신설 — 전화 사업자·STT 키 없는 개발용 테스트 콜"
assignee: "조서희"
role: "app"
status: "done"
sprint: 3
priority: 2
date: 2026-09-11
paths:
  - "services/gateway/*"
  - "apps/dashboard/src/lib/ws/types.ts"
---

## 무엇을

`services/gateway`(Node.js/Express/ws)를 새로 만들었다 — `hubClient.js`가
`POST /hub/calls`·`POST /hub/transcripts`를 호출해 마스킹을 거치고,
`dashboardHub.js`가 그 결과를 `apps/dashboard`용 WebSocket(`/dashboard`)으로 중계한다.

전화 사업자(Twilio 등) 연동은 만들지 않았다. 대신 `GET /dev` 페이지가 브라우저 내장
Web Speech API로 그 자리에서 텍스트로 바꿔 보낸다 — 오디오가 서버로 안 오므로 Google
STT 호출도, GCP 자격증명도 필요 없다.

`apps/dashboard/src/lib/ws/types.ts`의 `gatewayUrl()`에 `?gateway=<wss URL>` 쿼리 기반
런타임 오버라이드를 추가했다 — Vercel 빌드타임 환경변수 없이도 배포된 대시보드를
라이브 모드로 전환할 수 있다.

## 왜

담당 경계상 `services/gateway`는 정성윤 몫이다(`_project/decisions/012`). 포트폴리오
드래프트 단계에서 실제 폰으로 통화 테스트를 하며 개발을 진행하고 싶은데, 서버
운영자·백엔드 협조를 바로 받기 어려운 상황이라 `decisions/023`에 따라 직접
진행했다. 처음엔 Twilio + 서버 쪽 Google STT로 만들었다가, 전화 사업자 계정을 만들
단계가 아니고 STT 자격증명은 원래 류준·장민석 몫이라는 지적이 맞아 그 경로를
전부 지우고 지금 방식으로 바꿨다. 자세한 맥락·선택지·되돌리는 법은
`_project/decisions/402-services-gateway-실시간-배선과-dev-테스트-경로.md`에 남겼다.

## 완료 조건

- [x] `/dev` 페이지 → 게이트웨이 → 배포된 실제 백엔드(`server.solidbob.cloud`) →
  대시보드까지 엔드투엔드로 실측 확인 (2026-09-11, 실제 폰으로 "여보세요" 테스트)
- [x] `GET /hub/calls/{call_id}/transcript`로 DB 영구 저장 확인
- [x] Google STT 자격증명·전화 사업자 계정 없이 동작

## ⚠ 범위 밖

- **정식 A-1/A-2(실제 전화망 연동)는 여전히 미착수다.** `/dev`는 브라우저 STT
  품질이라 "게이트웨이→hub→대시보드" 배선 확인용이지, STT 품질 측정용이 아니다.
  실제 전화 연동이 필요해지면 전화 사업자를 새로 고르고 서버 쪽 Google STT 호출
  코드를 다시 만들어야 한다.
- `w2-stt-batch`(정성윤, 녹음 파일 배치 전사)와는 다른 기능이다 — 겹치지 않는다.
