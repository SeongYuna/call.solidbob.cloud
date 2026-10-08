---
title: "전사 암호화 운영 키 — `TRANSCRIPT_ENC_KEY` 생성·보관·주입과 배포 확인"
assignee: "정성윤"
role: "infra"
status: "done"
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

- [x] 루트 `.env.example` 에 `TRANSCRIPT_ENC_KEY=` 한 줄(값 없이) — 사용자가 직접 넣었다(2026-10-08)
- [x] 키 보관처 결정 — **SSM Parameter Store SecureString** `/callguard/prod/TRANSCRIPT_ENC_KEY`
- [x] 런북 12-2-d 대로 `server-env` 에 주입 → `/health` 의 `"transcript_encryption":"on"`
- [x] 배포 순서 확인 — 서버 `0.1.46` 이 미디에이터 `0.2.14` 보다 먼저 또는 함께. 미디에이터만 바뀌면 화면 원문 자막이 `/close` 요약에 마스킹 없이 섞인다
- [x] 19장 11번 — 응답 `text` 가 마스킹본, DB 의 새 행은 `enc:v1:…`

## 2026-10-08 — 켰다 (정성윤)

`/health` 가 **`"transcript_encryption":"on"`** 이다. server `0.1.49` · call-mediator `0.2.16`(PR #166 한 릴리스로 함께 — 배포 순서 조건 충족).

**① 보관처 — SSM Parameter Store SecureString** `/callguard/prod/TRANSCRIPT_ENC_KEY`(ap-northeast-2).
클러스터 밖이고 KMS 로 싸인다. Secrets Manager 는 월 과금·회전 기능까지라 과해서 쓰지 않았다.

**⚠ 런북 12-2-d 에 빠진 것이 있었다 — 노드에 Parameter Store 권한이 없었다.**
`callguard-ec2-role` 은 `AmazonSSMManagedInstanceCore`(원격 명령용) + `assist-s3-access` 뿐이라 `ssm:PutParameter` 가 없다.
그렇다고 키를 SSM `send-command` 로 노드에 보내면 **명령 본문이 30일간 기록에 남아** 누구나 다시 읽을 수 있다 — 자물쇠의 의미가 없어진다.
그래서 **역할에 좁은 인라인 정책 `transcript-enc-key` 를 더했다**:

- `ssm:PutParameter`·`ssm:GetParameter` — **그 파라미터 하나**에만(`Resource` 로 한정)
- `kms:Encrypt`·`kms:Decrypt` — `kms:ViaService = ssm.ap-northeast-2.amazonaws.com` 조건이 붙어 **SSM 을 거칠 때만**

`GetParameter` 까지 넣은 이유는 **복구 경로**다 — 클러스터를 다시 세우거나 시크릿이 날아가도 노드가 스스로 금고에서 키를 꺼내 온다.
되돌리기: `aws iam delete-role-policy --role-name callguard-ec2-role --policy-name transcript-enc-key`.

**② 절차** — 노드 안에서만 돌렸고 **키 값은 어디에도 출력하지 않았다**.
기존 파라미터·시크릿이 있으면 **덮어쓰지 않고 멈추도록** 먼저 검사했고(덮어쓰면 기존 암호문을 영원히 못 읽는다),
`server-env` 를 통째로 백업했으며(`/root/secret-backups/20261008-045600/`), **금고에 먼저 넣고 다시 읽어 같은지 확인한 뒤에야** 시크릿에 손댔다.
`rollout restart` 는 새 파드가 준비된 뒤 옛 파드를 내려 **중단 없이** 끝났다.

**③ 19장 11번 확인**(통화 `encverify-045718`)

| 보는 곳 | 값 |
|---|---|
| 화면 `/ws` | `제 번호는 010-9876-5432 이에요` — 원문(`326` 그대로) |
| API `GET /hub/calls/{id}/transcript` | `제 번호는 ************* 이에요` — **마스킹본**(서버가 풀어서 준다) |
| DB `transcript_segment.text` | **`enc:v1:wkzHqB9TibLIiOeN_I-nK6oJ…`** — 암호문 |
| 키 넣기 전 통화(`verify326-muz0sasl`) | `제 번호는 ************* 이에요` — **평문 그대로**(옛 행은 안 깨진다) |

**⚠ 종료 정리와 묶인다** — [w8-project-closeout](/backlog/w8-project-closeout/) 의 「키 폐기」를 그냥 하면
**이 키로 암호화된 전사를 영원히 못 읽는다.** 제출물·발표에 전사를 쓸 거면 **「자료 추출 → 키 폐기」** 순서를 그 티켓에 못 박는다.
런북도 「키를 지우지 않는다」고 경고한다.
