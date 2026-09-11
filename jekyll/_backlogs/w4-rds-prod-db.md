---
title: "운영 DB 를 RDS 로 — Neon 임시 연결 걷어내기"
assignee: "정성윤"
role: "infra"
status: "in-progress"
sprint: 4
priority: 1
date: 2026-09-11
requirement:
  - "SEC-1"
  - "SEC-2"
---

## 무엇을

운영 서버가 09-08 배포 이후 **DB 에 한 번도 연결되지 않았다**. 운영 시크릿이 임시로 Neon(싱가포르)을
가리키는데 `POSTGRES_HOST` 가 비어 있고, 운영 이미지 `0.1.1` 은 `DATABASE_URL` 을 읽지 않는다.
RDS 는 설계에만 있고 만들어진 적이 없다. RDS 를 만들어 운영 DB 로 옮긴다.
근거: [`_project/decisions/108`](https://github.com/SeongYuna/call.solidbob.cloud/blob/main/_project/decisions/108-운영-DB-를-Neon-임시에서-RDS-로-옮긴다.md)

## 왜

백업(RDS 를 고른 원래 이유) · 같은 리전 · 퍼블릭 비노출(SEC-1) · 개발·운영 분리.

## 완료 조건

- [x] DB 보안 그룹 `assist-db` — 5432 인바운드 소스가 운영 EC2 에 붙은 `assist-web` 과 같은 그룹이다
  (2026-09-11 런북 3-2 대조 명령으로 두 ID 일치 확인)
- [x] RDS `callguard-pg` — 생성됨. **마스터 사용자 `callguard` · 초기 DB `assist`**(2026-09-11 `describe-db-instances` 확인).
  PostgreSQL 17 · db.t4g.micro · 단일 AZ · 퍼블릭 액세스 아니요 · 백업 7일 · 삭제 방지는 콘솔에서 따로 확인한다

> **2026-09-11 이름 정정** — 처음엔 AWS 자원까지 `callguard-*` 로 적었는데, 그건 k8s 오브젝트 이름이다.
> AWS 자원은 원안 `assist-*`(EC2 보안 그룹 `assist-web`)이고 RDS 만 식별자·사용자가 `callguard`, **DB 는 `assist`** 다.
> 연결 문자열은 `…:5432/assist?sslmode=require`. 런북 6·12-2·17 을 이 값으로 고쳤다.
- [x] 클러스터 안에서 접속 확인 — 서버 파드에서 `('assist', 'callguard') ssl True` (2026-09-11, 런북 17-1)
- [x] `db/schema.sql` 적용 — 22 테이블 (2026-09-11, 런북 17-2 · `main` 의 파일)
- [x] `server-env` 교체 — `DATABASE_URL`·`POSTGRES_*` 둘 다 RDS, AWS 정적 키 제거, 재시작 (2026-09-11).
  ⚠ 첫 시도는 **암호가 빈 값**으로 들어가 `fe_sendauth: no password supplied` 였다 — 웹 터미널에 붙여 넣을 때 딸려 온
  빈 Enter 를 `read` 가 먼저 받았다. 빈 입력이면 다시 묻는 반복문으로 바꿔 넣었다(런북 12-2 에 반영할 것)
- [x] 운영 `GET /hub/knowledge-gaps` **200** (`{"gaps":[],"total":0,…}`, 2026-09-11) — 운영이 DB 에서 읽은 첫 응답.
  파드 로그의 `psycopg` 오류 여부는 보지 않았다
- [ ] 백업 `~/server-env.backup.yaml` 삭제(`shred -u`) — `0.1.2` 배포 확인 뒤
- [x] 런북 6·12-2·17·19장을 실물(`callguard` 이름, `server-env`)에 맞춰 수정 — 2026-09-11. `secret.example.yaml` 도 함께
  (`DATABASE_URL`·`POSTGRES_*` 둘 다 · `sslmode=require` · AWS 키 제외)

> **런북을 따르면 순서가 위 목록과 조금 다르다** — 6(RDS) → **12-2(시크릿 교체·재시작)** → 17-1(접속 확인) →
> 17-2(스키마) → 19(검증). 접속 확인과 스키마 적용을 **서버 파드 안에서 서버와 같은 `DATABASE_URL` 로** 하므로
> 시크릿을 먼저 바꿔야 한다. `psql` 파드는 쓰지 않는다(암호를 명령줄에 넘기지 않으려고).

⚠ 전사 저장(`POST /hub/transcripts`)은 이 티켓으로 살아나지 않는다 — [w4-schema-qa-followup](/backlog/w4-schema-qa-followup/) ①
(어댑터 복합키) + 이미지 `0.1.2` 가 필요하다.
