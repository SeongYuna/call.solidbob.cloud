---
title: "로컬 서버 API 를 ngrok 으로 조서희에게 연다 (정성윤 부재 중 프론트 연동)"
assignee: "장민석"
role: "ai"
status: "in-progress"
sprint: 3
priority: 2
date: 2026-09-10
depends_on:
  - "w3-call-start-api"
paths:
  - "server/requirements.txt"
---

## 무엇을

운영 서버는 ES 적재가 안 돼 있고 정성윤이 부재라, **내 로컬 서버(Neon + 로컬 ES)를 ngrok 으로
내보내** 조서희가 실서버 응답으로 대시보드를 맞춰 보게 한다. Vercel·게이트웨이는 건드리지 않는다 —
프론트가 필요한 것은 API 주소 하나다.

## 조서희에게 줄 것

- 주소: `https://grandma-unwritten-scouring.ngrok-free.dev` (임시 도메인 — ngrok 재시작 시 바뀐다. 고정 도메인은 대시보드에서 아직 안 만들었다) · Swagger `/docs`
- 순서: `POST /hub/calls {"call_id": "test-…", "stt_engine": "mock"}` → `POST /hub/transcripts` → `POST /hub/recommendations`
- 브라우저 `fetch` 에는 `ngrok-skip-browser-warning: 1` 헤더를 붙인다(무료 플랜 경고 페이지 우회). CORS 는
  `localhost:5173`·`call.solidbob.cloud` 를 열어 뒀다.
- **응답 필드는 전부 문자열이다**(09-10 오후 합의). 불리언 `"true"`/`"false"`, 숫자 `"3150"`, `null` 은 그대로. 요청은 정수·불리언·숫자 문자열 전부 받는다.
- ⚠ `trigger_at_ms`·`internal_latency_ms` 는 모형값이다(도착 시각이 계약에 없다).

## 완료 조건

- [x] 로컬 서버가 스포크 4종으로 뜬다 · 통화 시작 → 전사 → 추천이 실제 응답으로 돈다
- [x] ngrok authtoken (사용자 계정) · [ ] 고정 도메인 — 대시보드 Domains 에서 만들면 주소가 고정된다
- [x] basic auth 는 **일부러 안 건다** — 브라우저 CORS preflight(OPTIONS)에는 Authorization 이 안 실려 ngrok 이 401 로 막고, 그러면 fetch 자체가 실패한다. 근거는 [미결](/open-items/)
- [ ] 조서희가 그 주소로 `/health`·`/hub/recommendations` 응답을 받았다
