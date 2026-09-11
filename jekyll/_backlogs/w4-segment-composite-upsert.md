---
title: "전사 저장 복합키 반영 + 이미지 0.1.2 — 운영에서 통화 시작·전사 저장 살리기"
assignee: "정성윤"
role: "infra"
status: "in-progress"
sprint: 4
priority: 2
date: 2026-09-11
requirement:
  - "A-1"
  - "C-5"
  - "SEC-1"
paths:
  - "server/apps/hub/adapter/outbound/postgres/transcript_segment_repository.py"
  - "server/apps/hub/adapter/outbound/postgres/transcript_query_repository.py"
  - "server/apps/hub/adapter/inbound/api/v1/transcript_ingest_router.py"
  - "server/apps/hub/app/ports/output/transcript_ingest_record_port.py"
  - "infra/k8s/base/kustomization.yaml"
  - "server/conftest.py"
  - ".github/workflows/test.yml"
---

## 무엇을

운영 `server.solidbob.cloud` 에 **통화를 만드는 엔드포인트가 없다** — 새 통화 ID 로 `POST /hub/transcripts`
를 보내면 500 이고, 게이트웨이 쪽에서는 그 구간이 조용히 버려진다(2026-09-11 보고).

`POST /hub/calls` 는 09-10 에 이미 코드로 있다([w3-call-start-api](/backlog/w3-call-start-api/),
`_project/decisions/301`). 운영에 없는 이유는 이미지 태그가 `0.1.1` 그대로라 새 이미지가 구워지지
않았기 때문이다. **그런데 태그만 올리면 안 됐다** — 전사 저장 어댑터가 09-09 스키마 QA(`decisions/205`)
이후의 스키마와 어긋나 있었다. [w4-schema-qa-followup](/backlog/w4-schema-qa-followup/) ① 을 이 티켓으로 떼어 왔다
(장민석 티켓의 ③ 은 그대로 남는다).

## 어떻게

- `transcript_segment_repository.py` — `ON CONFLICT ("segment_id")` → `("call_id", "segment_id")`,
  `masking_event` 삭제·삽입에 `call_id` 를 함께 넣는다(복합 FK).
- `transcript_query_repository.py` — 마스킹 구간 조회를 `call_id` 로 거른다. 안 거르면 다른 통화의 같은 순번
  구간이 섞여 나온다(같은 결함의 읽기 쪽).
- 통화 시작 전 전사 → **500 대신 409 + "POST /hub/calls 를 먼저"**. 외래키 위반(SQLSTATE 23503)만
  바꾸고 다른 DB 오류는 그대로 올린다.
- `infra/k8s/base/kustomization.yaml` `newTag` `0.1.1` → `0.1.2`.

## 완료 조건

- [x] 두 통화의 같은 순번 발화가 각각 남는 테스트 — 실제 PostgreSQL 16 + 현재 `db/schema.sql`(22 테이블)에서 통과
- [x] 수정 전 코드가 같은 DB 에서 실패함을 확인 — `InvalidColumnReference: no unique or exclusion constraint matching the ON CONFLICT`
- [x] `server` 315 passed · 계약 4종 KEPT / `ai` 191 passed · 계약 3종 KEPT
- [x] 재발 방지 — CI `server` job 이 `postgres:17` + 현재 `schema.sql` 로 integration 테스트를 돈다(로컬 재현: 수정 전 어댑터 2 failed)
- [x] 위 CI 가 첫 PR 에서 실제로 초록인지 확인 — PR #64 `server` job: 스키마 22 테이블 · **integration 4 passed**
- [x] **운영 DB 가 새 스키마인 상태에서** 머지 — RDS 전환 뒤 PR #64 머지(`3514e18`), `release.yml` plan·image·deploy 성공
- [x] 운영 확인(2026-09-11): `/openapi.json` 에 `POST /hub/calls` · 통화 시작(`created "true"`, 재알림 `"false"`) →
  전사 **200**(`제 번호는 *********** 입니다`, P4) → 조회 `total 1` · 시작 안 한 통화 **409**
- [ ] `/health` `spokes` 에 `trigger` — **`0.1.2` 에서 빠졌다.** `server.Dockerfile` 이 `ai/apps/` 만 복사하고 `ai/provider.py`
  를 안 담아 `main.py` 가 트리거를 조용히 못 꽂았다(이미지 배치를 흉내 내 재현). `COPY ai/provider.py` + `0.1.3` +
  재발 방지 테스트(`server/tests/test_image_layout.py`)를 준비했다 — 배포 대기
