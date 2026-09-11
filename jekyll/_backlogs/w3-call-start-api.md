---
title: "통화 시작 API — POST /hub/calls (전사 저장의 외래키 선행 조건)"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 3
priority: 1
date: 2026-09-10
requirement:
  - "SEC-1"
  - "SEC-2"
paths:
  - "server/apps/hub/app/dtos/call_start_dto.py"
  - "server/apps/hub/app/use_cases/call_start_interactor.py"
  - "server/apps/hub/adapter/inbound/api/v1/call_start_router.py"
  - "server/apps/hub/adapter/outbound/postgres/call_repository.py"
  - "server/apps/hub/adapter/outbound/postgres/connection.py"
  - "server/main.py"
---

## 무엇을

`transcript_segment.call_id → call` 외래키 때문에 통화가 먼저 있어야 전사가 저장되는데,
`call` 행을 만드는 경로가 없었다. Neon 에 실제로 쳐 보니 `POST /hub/transcripts` 가 첫 건부터
저장에서 500 이었다. 근거·선택지: `_project/decisions/301`.

## 어떻게

- 슬라이스 `call_start` — `schema → router → dto → input port → interactor → output port → adapter → provider → test`
  단면 전부. 멱등(`ON CONFLICT DO NOTHING`, 응답 `created`).
- 같은 경로에서 드러난 수정 둘 — ① 커넥션 팩토리가 `DATABASE_URL` 을 안 읽던 것(운영은 그것만
  주입한다, 런북 12-2) ② ES 인덱스 없을 때 500 → 503 + 이유.
- `main.py` 트리거 스포크 배선 — 류준이 [w3-trigger-v1](/backlog/w3-trigger-v1/)에 남긴 안내대로
  `ai/provider.py` 팩토리를 꽂았다. 마지막 501 이 풀렸다.

## 완료 조건

- [x] `POST /hub/calls` → `POST /hub/transcripts` → `POST /hub/recommendations` 가 Neon + 로컬 ES 로 끝까지 돈다
- [x] 같은 `call_id` 재알림이 200 + `created: false`
- [x] `/health` `spokes` 에 `trigger` 가 뜬다
- [x] `server` 286 통과 · 계약 4종 KEPT
