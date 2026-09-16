---
title: "테스트 음성 업로드·보관 — presign 발급 지점 + 브라우저 페이지"
assignee: "정성윤"
role: "infra"
status: "done"
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
- [x] **버킷 CORS 규칙** (2026-09-14 콘솔) — 오리진 `https://server.solidbob.cloud` 하나 · `POST`·`GET` · `*` 아님.
      ⚠ EC2 역할에는 `s3:PutBucketCors`·`GetBucketCors` 가 없다 — 설정도 확인도 **콘솔에서만** 된다.
      진짜 검증은 배포 뒤 브라우저 업로드 성공 여부다
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
- [x] `.env.example` 에 `S3_BUCKET`·`UPLOAD_TOKEN`·`UPLOAD_MAX_BYTES` (`AWS_REGION` 은 이미 있었다).
      값 없는 키 추가라 자격증명 보호 훅에 걸리지 않았다. `core/config.py` 와 1:1 대조 확인
- [x] **`kustomization.yaml` 의 `newTag` 를 올린다** — `server/` 를 고치므로 안 올리면 릴리스가 실패한다(오늘까지 네 번 겪었다)
- [x] **운영 `server-env` 주입** (2026-09-14) — `S3_BUCKET=assist-apne2` · `AWS_REGION` · `UPLOAD_TOKEN`(32바이트) ·
      `UPLOAD_MAX_BYTES`. 키 목록으로 확인했고 **`AWS_ACCESS_KEY_ID`·`AWS_SECRET_ACCESS_KEY` 는 없다**(`108` ③ 유지).
      ⚠ SSM 에서 `K=` 변수가 붙여넣기에 씹혀 `patch: command not found` 가 났다 — **전체 명령을 한 줄씩** 쳐서 해결.
      같은 이유로 첫 백업이 **0바이트**로 만들어졌다(리다이렉트만 실행됨). 다시 떴다
- [x] **운영 관통 확인 완료 (2026-09-15).** `0.1.6` 배포 · `/health` `spokes` 에 `uploads` ·
      토큰 없이 401 · 틀린 토큰 401 · 페이지 200. **브라우저에서 실제로 한 건 올라갔다** —
      `s3://assist-apne2/uploads/2026-09-15/a2d7f69a-…​.mp3` (30.6KB · Standard, 콘솔 확인).
      이 한 건이 **CORS · presigned POST · IAM 역할(IMDSv2) · 키 생성 규칙 · 확장자 보존**을 한 번에 증명한다 —
      CORS 는 브라우저만 적용하므로 curl 로는 끝까지 검증할 수 없었다

## 하지 않는 것

- 자체 통화 녹음 업로드 (절대 원칙 7 — AI Hub 등 출처가 해결된 것만)
- 버킷 신설 (프리픽스 `uploads/` 로 충분 — `110` 6번)
- 퍼블릭 액세스 차단 해제 (presigned 는 차단과 무관하게 동작 — `110` 8번)
