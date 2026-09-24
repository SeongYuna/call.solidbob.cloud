---
title: "읽기 경로 인증 — 통화 목록·전사·기록·검색이 무인증이고 지식 공백 설명이 마스킹 없이 저장된다"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 6
priority: 58
date: 2026-09-22
requirement:
  - "SEC-1"
paths:
  - "server/apps/hub/*"
---
> **정성윤이 09-22 저녁 최종 QA(류준 페르소나 4 + 검증 웨이브)·운영 확인 결과를 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

운영에서 토큰 없이 열린다(09-22 최종 QA 실측): `GET /hub/calls`(12건 · 실제 음성 테스트 통화 포함 · 고객 HMAC · `?customer_id=` 필터) ·
`/transcript` · `/record` · `GET/POST/PATCH /hub/knowledge-gaps`(**설명이 마스킹 없이 저장**) · `POST /hub/search`.
쓰기 경로는 09-22 fail-closed 로 닫혔다(PR #131). **09-30 전에 닫히지 않은 가장 큰 구멍**이다.

## 어떻게

1. 라우터 표(경로 · 지금 문 · 걸 문 — 상담원 토큰 / 서비스 토큰 / 관리자 세션)를 결정 기록 `3xx` 로
2. `knowledge-gaps` 설명은 저장 전에 마스킹 스포크를 태운다(SEC-1)
3. 화면이 토큰을 싣는 것(`w6-read-path-token-ui`, 조서희)과 **같은 릴리스**에 — 먼저 걸면 화면이 깨진다

## 완료 조건

- [x] 결정 기록 + 라우터 표
- [x] 토큰 없는 GET 이 401 인 테스트(경로마다)
- [x] `knowledge-gaps` 저장본에 원문이 없는 테스트

근거: 미결 「읽기 경로 인증 없음」 · 마감 체크리스트 13번.

## 2026-09-22 — 장민석 착수·서버 구현 (담당 확인)

- 결정 기록 + 라우터 표: `decisions/322`. **부르는 쪽을 코드로 보고 갈랐다** — 상담원 화면 읽기 넷은 토큰을 안 실어 `120` 처럼 두 단계(지금은 상담원·서비스 토큰을 받고 틀리면 401, `READ_AUTH_REQUIRED=true` 로 닫음 · `/health` `read_guard`). 관리자 화면은 이미 관리자 토큰을 실어 지식 공백 조회·집계·상태 변경은 **바로 닫았다**. 신고는 부르는 곳이 없어 상담원 토큰으로 바로 닫음
- 테스트: `tests/test_main_read_guard.py`(경로마다 — 켜면 없음 401 · 상담원/서비스 토큰 통과 · 이행기에도 틀린 토큰 401) · `test_knowledge_gap_guards.py` · 신고 설명 마스킹(`test_knowledge_gap_interactor`)
- `e2e_check.py` 가 `INGEST_SERVICE_TOKEN` 이 있으면 읽기에 싣는다
- ⚠ 「같은 릴리스」 대신 두 단계로 갔다 — 서버를 먼저 내도 화면이 깨지지 않고, 조서희 님(`w6-read-path-token-ui`)이 싣는 즉시 `server-env` 한 줄로 닫는다. 남은 것: 그 한 줄

## 2026-09-22 — 배포

- **`0.1.35` 운영 배포됨** (PR #132 머지 07:57 → release 성공 · `/health` `version: 0.1.35` · `read_guard: open` 확인, 09-22)
- 남은 것: `w6-read-path-token-ui`(조서희) 뒤 `server-env` 에 `READ_AUTH_REQUIRED=true` → `read_guard: locked`

## 2026-09-23 — 조서희, 프론트 쪽 붙였다

`w6-read-path-token-ui` 완료 — `coreClient.ts`의 네 함수(`fetchCallList`·`fetchCallTranscript`·
`fetchCallRecord`·`searchDocuments`)가 이제 상담원 토큰을 싣는다. **`server-env`의
`READ_AUTH_REQUIRED=true`를 켜도 되는 상태다** — 코드 배포 없이 그 한 줄만 남았다.

## 2026-09-23 — 문을 닫았다 (정성윤)

**마지막 한 줄은 서버가 아니라 운영 설정이었다.** 조서희 님이 `24f7df4`(PR #145)로 읽기 넷에 상담원 토큰을
싣기 시작했고 배포까지 확인된 뒤, 운영 시크릿 `server-env` 에 `READ_AUTH_REQUIRED=true` 를 넣고
`callguard-server` 를 다시 띄웠다(SSM, 11:5x). 이미지는 그대로 `0.1.38` — 코드 배포가 아니다.

확인한 것 — `/health` `read_guard: **locked**` · 토큰 없이 `GET /hub/calls` · `GET /hub/calls/{id}/transcript` ·
`POST /hub/search` 전부 **401** · 틀린 토큰도 401 · `/health/ready` 200(문과 무관하게 살아 있다).

- 되돌리기: `kubectl -n callguard patch secret server-env --type json -p '[{"op":"remove","path":"/data/READ_AUTH_REQUIRED"}]'`
  뒤 `rollout restart deploy/callguard-server`. 30초, 이미지 그대로. 상태는 `/health` 의 `read_guard` 가 말한다.
- **Q-14 는 절반만 닫힌다(2026-09-23 정정).** 이 티켓이 닫은 것은 **바깥문**이다 — 토큰 없는 사람은 못 읽는다.
  **로그인한 상담원에게 남의 통화가 보이는 것은 그대로다**: `GET /hub/calls` 가 요청자를 안 보고,
  통화에 `agent_id` 가 안 채워진다(`call_repository.py` 머리말). 운영 화면에서 09-22 통화 다섯 건이
  새 로그인에도 보였다. 남은 절반은 [w8-call-owner-scope](/backlog/w8-call-owner-scope/) 로 옮겼다 —
  **재시험 때 Q-14 는 ✅ 가 아니라 ⚠ 로 적는다.**
