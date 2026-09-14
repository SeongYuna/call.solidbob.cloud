---
title: "게이트웨이 하나로 — /dev 브라우저 음성 경로를 정식 게이트웨이로 옮긴다"
assignee: "정성윤"
role: "infra"
status: "done"
sprint: 4
priority: 2
date: 2026-09-11
requirement:
  - "A-3"
  - "SEC-1"
paths:
  - "services/gateway/src/*"
depends_on:
  - "w4-gateway-streaming-stt"
---

**같은 `services/gateway` 에 게이트웨이가 둘 생겼다.** 조서희 님이 frontend 브랜치에서 브라우저 내장 음성
인식(Web Speech API)으로 글자를 보내는 개발용 경로를 만들었고(`w3-gateway-dev-testcall` — frontend 브랜치에만 있다,
`decisions/402`), 같은 날 main 에는 서버 쪽 Google STT 로 전사하는 정식 게이트웨이가 들어가 배포됐다
([w4-gateway-streaming-stt](/backlog/w4-gateway-streaming-stt/)). 기능은 겹치지 않는데 **자리가 겹친다** —
합치면 `README`·`package.json` 이 충돌하고 한 디렉터리에 서버가 둘이 된다.

## 무엇을 — 하나로 합친다 (`decisions/109`)

- 정식 게이트웨이를 기준으로 두고, 조서희 님 `/dev` 의 쓸모(GCP 키 없이 폰으로 바로 테스트)를 **입력 방식 하나로** 옮긴다
- `GET /dev` 페이지 → 브라우저 음성 인식 → `WS /dev/text` (글자) → 같은 파이프라인(서버 마스킹 → 대시보드)
- 통화 기록의 STT 엔진을 사실대로 `web-speech` 로 적는다. 구글 STT 를 안 쓰므로 COST-1 캡과 무관하다
- 운영에서는 `https://server.solidbob.cloud/gateway/dev` — 이미 HTTPS 라 ngrok 이 필요 없다
- 조서희 님 대시보드 경로 `/dashboard` 를 `/ws` 의 별칭으로 받는다

## 지키는 것

- 글자 입력도 DB 에 쓰므로 **과금 문과 같은 토큰**(`GATEWAY_INGEST_TOKEN`)을 요구한다. 브라우저는 헤더를 못 붙이므로
  WebSocket 서브프로토콜로 낸다 — URL 에 비밀을 싣지 않는 원칙 그대로
- **ngrok 같은 터널은 루프백으로 들어온다.** 프록시 헤더가 붙은 루프백 요청은 믿지 않는다 — 안 그러면 터널로 연 순간 문이 열린다
- `apps/`(조서희 님 전담)와 frontend 브랜치는 건드리지 않는다 — 합칠 때 할 일은 [미결](/open-items/)에 남긴다

## 완료 조건

- [x] `/dev`·`/dev/text` + 테스트(79), 게이트웨이 태그 `0.1.1` 로 배포 — PR #69
- [x] 운영 `/gateway/dev` 200 · CSP 해시 일치 · 토큰 없는 `/gateway/dev/text` 401 (2026-09-11)
- [x] `decisions/109`, 미결(frontend 합칠 때 할 일)
