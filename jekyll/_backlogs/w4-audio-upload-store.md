---
title: "테스트 음성 업로드·보관 — presign 발급 지점 + 브라우저 페이지"
assignee: "정성윤"
role: "infra"
status: "in-progress"
sprint: 4
priority: 3
date: 2026-09-14
requirement:
  - "A-6"
  - "SEC-1"
  - "SEC-2"
  - "COST-1"
paths:
  - "server/apps/hub/*"
---

## 무엇을

팀원 넷이 **각자 브라우저에서** 테스트 음성을 올리고, 올린 것이 **S3 에 남아** 나중에 다시 듣고
재처리할 수 있게 한다. 발급 지점은 `server`, 문은 토큰이다.
근거: [`_project/decisions/110`](https://github.com/SeongYuna/call.solidbob.cloud/blob/main/_project/decisions/110-테스트-음성-파일을-S3-에-보관한다-발급은-server-문은-토큰.md)

## 왜

기존 세 경로(`scripts/stream_wav.ts` · `GET /gateway/dev` · `WS /gateway/ingest`)는 **흘려보내고 끝난다.**
같은 음성으로 다시 돌려 비교하려면 보관이 필요하고, 정성윤 노트북에서만 되는 절차는 팀 도구가 아니다.

## 완료 조건

- [x] **선행 — 파드 자격증명 판정.** 2026-09-14 운영 파드에서 IMDSv2 로 확인 —
      「토큰 발급 성공 → 역할: `callguard-ec2-role`」. **추가 자격증명이 필요 없다**
      (hop limit 인상도, 전용 IAM 사용자도 불필요). `server-env` 에 AWS 키를 넣지 않는다
- [ ] **버킷 CORS 규칙** — 오리진 `https://server.solidbob.cloud` 하나, 메서드 `POST`·`GET`, `*` 금지.
      콘솔 → S3 → `assist-apne2` → 권한 → CORS. **이게 없으면 브라우저 업로드가 100% 막힌다**
- [x] ~~`server/apps/uploads/` 슬라이스~~ → **`server/apps/hub/` 수직 슬라이스로 넣었다.**
      `masking`·`blacklist` 는 HTTP 가 없는 **규칙 스포크**이고 라우터는 전부 `hub` 에 있다
      (`server/CLAUDE.md` §2). 업로드는 규칙 판정이 아니라 요청 경로라 `hub` 가 맞다 —
      새 root package 를 만들지 않아 `.importlinter` 도 건드릴 일이 줄었다.
      presigned **POST**(`content-length-range` 상한) · 키는 서버 생성 · 만료 5분
- [x] `UPLOAD_TOKEN` fail-closed — 미설정이면 전부 거절. `Authorization: Bearer` 로만 받고 URL 에 싣지 않는다
- [x] 목록 · 다시 듣기(GET presign) — 객체를 공개로 만들지 않는다
- [x] 브라우저 페이지 — 팀원이 토큰 붙여넣고 파일 고르면 끝. `services/gateway/src/adapters/dev_page.ts` 와 같은 모양
- [x] 테스트 — 토큰 없음/틀림 거절 · 크기 초과 거절 · 클라이언트가 준 키 경로가 무시되는지(`../`·`datasets/`)
- [x] `boto3==1.35.76` 을 `server/requirements.txt` 에. `root_packages` 추가는 **불필요**(hub 안이다).
      대신 **계약 3 에 `boto3` 를 금지 목록으로 추가** — `hub.app` 은 S3 를 모른다. 계약 4종 KEPT
- [x] `secret.example.yaml` 에 `S3_BUCKET`·`AWS_REGION`·`UPLOAD_TOKEN`·`UPLOAD_MAX_BYTES` (YAML 파싱 확인)
- [ ] **`.env.example` — 사람이 넣는다.** 자격증명 보호 훅이 이 파일 편집을 막는다(`server/CLAUDE.md` §6)
- [x] **`kustomization.yaml` 의 `newTag` 를 올린다** — `server/` 를 고치므로 안 올리면 릴리스가 실패한다(오늘까지 네 번 겪었다)
- [ ] 운영 확인 — `0.1.5` 배포 후 브라우저에서 한 건 올리고 `aws s3 ls s3://assist-apne2/uploads/` 로 보인다.
      `/health` 의 `spokes` 에 `uploads` 가 추가된다(스모크 테스트는 부분집합 검사라 영향 없다)

## 하지 않는 것

- 자체 통화 녹음 업로드 (절대 원칙 7 — AI Hub 등 출처가 해결된 것만)
- 버킷 신설 (프리픽스 `uploads/` 로 충분 — `110` 6번)
- 퍼블릭 액세스 차단 해제 (presigned 는 차단과 무관하게 동작 — `110` 8번)
