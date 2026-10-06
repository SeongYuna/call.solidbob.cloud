---
title: "전사 암호화 운영 키 — `TRANSCRIPT_ENC_KEY` 생성·보관·주입과 배포 확인"
assignee: "정성윤"
role: "infra"
status: "todo"
sprint: 8
priority: 6
date: 2026-10-06
requirement:
  - "SEC-1"
  - "SEC-2"
depends_on:
  - "w8-screen-plain-storage-encrypt"
---

> 장민석이 넘긴 일이다(2026-10-06). 코드·문서는 [w8-screen-plain-storage-encrypt](/backlog/w8-screen-plain-storage-encrypt/)(장민석)에서 끝났고,
> 여기는 **운영 시크릿·배포** 몫이다. 근거: `_project/decisions/326`(비공개).

## 무엇을

server `0.1.46` 부터 `TRANSCRIPT_ENC_KEY` 가 있으면 `transcript_segment.text` 에 마스킹본을 AES-256-GCM 으로 싸서 넣는다.
**키가 없으면 지금처럼 마스킹본 평문**이라 키 없이 배포해도 깨지지 않는다.

## 왜 사람이 하나

- `.env.example` 은 자격증명 보호 훅이 Claude 편집을 막는다(SEC-2 체크리스트)
- `server-env` 시크릿은 운영 클러스터에서만 바꾼다(런북 12-2)
- **키를 잃으면 암호화된 전사를 되돌릴 수 없다** — 보관처를 정하는 것이 먼저다

## 완료 조건

- [ ] 루트 `.env.example` 에 `TRANSCRIPT_ENC_KEY=` 한 줄(값 없이)
- [ ] 키 보관처 결정(SSM Parameter Store SecureString 등 — 클러스터 밖)
- [ ] 런북 12-2-d 대로 `server-env` 에 주입 → `/health` 의 `"transcript_encryption":"on"`
- [ ] 배포 순서 확인 — 서버 `0.1.46` 이 미디에이터 `0.2.14` 보다 먼저 또는 함께. 미디에이터만 바뀌면 화면 원문 자막이 `/close` 요약에 마스킹 없이 섞인다
- [ ] 19장 11번 — 응답 `text` 가 마스킹본, DB 의 새 행은 `enc:v1:…`
