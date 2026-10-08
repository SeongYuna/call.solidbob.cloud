---
title: "상담원 화면은 원문, 저장은 마스킹 + 전사 본문 암호화 — C-5 위치를 저장 앞단으로 옮긴다"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 8
priority: 5
date: 2026-10-06
requirement:
  - "C-5"
  - "SEC-1"
  - "SEC-2"
paths:
  - "server/apps/hub/adapter/outbound/transcript_text_cipher.py"
  - "server/apps/hub/dependencies/transcript_cipher_provider.py"
  - "server/apps/hub/app/use_cases/postcall_interactor.py"
  - "services/call-mediator/src/app/call_registry.ts"
---

> 근거: `_project/decisions/326`(비공개). 사용자 결정(2026-10-06) — 상담원에게는 정보를 다 보여 주고, 저장할 때 마스킹·암호화한다.
> **프론트엔드(`apps/`)는 고치지 않는다**(사용자 지시) — 서버·콜 미디에이터·인프라에서 바꾼다.

## 무엇을

1. **화면** — 콜 미디에이터가 `/ws` 자막에 **원문**을 싣고 서버의 마스킹 구간은 그대로 둔다(화면이 그 자리를 강조).
   마스킹본과 원문의 길이가 다르면 원문을 싣지 않는다. 하류(추천·콜 가드·컴플라이언스·필요서류)에는 지금처럼 마스킹본
2. **`/close`** — 화면이 원문을 갖게 되므로, 서버가 받은 자막을 **요약 전에 마스킹**한다(요약 초안이 DB 에 저장된다)
3. **저장** — `transcript_segment.text` 에 마스킹본을 **AES-256-GCM** 으로 싸서 넣는다(`TRANSCRIPT_ENC_KEY`).
   키가 없으면 지금처럼 평문 마스킹본 · 형식이 틀리면 서버가 뜨지 않는다 · 옛 평문 행은 그대로 읽는다.
   읽는 곳 둘(지난 통화 보기 · 블랙리스트 근거)이 푼다. `/health` 에 `transcript_encryption`

## 완료 조건

- [x] 서버·콜 미디에이터 코드 + 테스트 (로컬 통과 — 진행 기록 2026-10-06-01)
- [x] 결정 기록 326 · 런북 12-2-d · `secret.example.yaml` · 배포 태그 server `0.1.46` · call-mediator `0.2.14`
- [x] 커밋 · PR 머지 — **PR #166, 2026-10-08**(충돌 셋 해소 · 태그 `0.1.49`·`0.2.16`)
- [x] 운영 확인: 화면 자막이 원문으로 나온다 — **2026-10-08 확인(정성윤)**. 아래 기록 참고

**넘긴 것**(2026-10-06 — 담당이 달라 티켓을 나눴다):
- 운영 키 생성·보관·주입 · `.env.example` · 배포 순서 확인 → [w8-transcript-enc-key-ops](/backlog/w8-transcript-enc-key-ops/)(정성윤)
- 화면 문구(잠금 아이콘 「민감정보가 마스킹되었습니다」 등) → [w8-agent-screen-plain-copy](/backlog/w8-agent-screen-plain-copy/)(조서희)

## 2026-10-08 — 운영 확인, 닫는다 (정성윤 — 운영 토큰이 있는 사람 몫)

PR #166 을 머지해 **server `0.1.49` · call-mediator `0.2.16`** 이 운영에 떴다(릴리스 성공 · `/health` `version: 0.1.49`).
운영 미디에이터 파드 안에서 `/dev/text` 로 한 줄을 흘리고 `/ws` 로 받아 양쪽을 같이 봤다(`verify326-muz0sasl`).

| 보는 곳 | 값 |
|---|---|
| 화면 `/ws` 자막 | `제 번호는 010-9876-5432 이에요` — **원문** |
| 같은 프레임의 `masked` | `[{"type":"P4","span":["6","19"]}]` — 가릴 자리는 따로 온다 |
| 자막 밖 메시지 4종 | `started`·`routing_decision`·`recommendation_pending`·`recommendation` — **넷 다 원문 없음** |
| API `GET /hub/calls/{id}/transcript` | `제 번호는 ************* 이에요` — **마스킹본** |
| DB `transcript_segment.text` | 같은 마스킹본 **평문**(`enc:v1:` 아님 — 운영 키가 아직 없다) |

**설계대로다** — 화면은 원문 + 그 자리 강조, 저장은 마스킹본, 하류 메시지에는 원문이 안 샌다.
코드·문서는 장민석, 운영 확인은 정성윤.

**남은 둘은 다른 티켓이다** — 운영 암호화 키([w8-transcript-enc-key-ops](/backlog/w8-transcript-enc-key-ops/), 정성윤) ·
화면 문구([w8-agent-screen-plain-copy](/backlog/w8-agent-screen-plain-copy/), 조서희).
⚠ 확인에 쓴 통화 `verify326-muz0sasl` 이 운영 DB 에 남아 있다 — 촬영 통화 일곱 건과 함께 지울지 정한다(미결).
