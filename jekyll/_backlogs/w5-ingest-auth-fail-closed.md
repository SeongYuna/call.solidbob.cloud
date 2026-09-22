---
title: "쓰기 경로 인증 3·4단계 — 시크릿 주입 → 서버 fail-closed"
assignee: "정성윤"
role: "infra"
status: "done"
sprint: 5
priority: 60
date: 2026-09-21
requirement:
  - "SEC-2"
paths:
  - "infra/k8s/base/*"
---

## 무엇을

`decisions/120` 의 남은 두 단계를 운영에서 끝낸다 — ③ 서비스 토큰을 **콜 미디에이터 시크릿에 먼저**,
그다음 `server-env` 에 넣고 ④ 서버를 fail-closed 로 바꾼다.

## 왜 지금인가

`120` 은 「두 이미지가 배포된 뒤에」로 미뤄 뒀다. **그 조건이 풀렸다** — 2026-09-21 `release.yml` 이
PR #106 까지 성공했고(저장소 `newTag` server `0.1.23` · call-mediator `0.2.2`), 같은 날 밖에서 본
`/health` 가 **`"ingest_guard":"open"`** 을 돌려준다. 그 필드는 `0.1.19` 에서 생겼으니 새 서버가 떠 있고,
**문은 아직 열려 있다.** 쓰기 일곱 경로가 토큰 없이 받는 상태다.

## ⚠ 순서를 바꾸면 운영 통화가 전부 401 이 된다

미디에이터가 토큰을 보내기 전에 서버가 요구하기 시작하면 통화 시작·전사 저장이 전부 거절된다.
**미디에이터 시크릿(`CORE_API_TOKEN`) → 롤아웃 확인 → 서버(`INGEST_SERVICE_TOKEN`)** 순서다. 두 값은 같아야 한다.

## 같이 닫는 것 — 새 클러스터에서 토큰이 조용히 비는가

`call-mediator.yaml` 은 `call-mediator-tokens` 에서 `CORE_API_TOKEN` 을 **optional** 로 읽는데
`release.yml` 의 시크릿 생성은 INGEST·VIEW 두 키만 만든다([미결 항목](/open-items/) 09-21). 사람이 넣는 전제라면
런북 12장에 그 단계를 적고, 아니면 워크플로에 넣는다.

## 완료 조건

- [ ] 미디에이터 시크릿에 토큰 주입 → 롤아웃 → 테스트 통화 1건이 그대로 저장된다
- [x] `server-env` 에 같은 값 주입 → `/health` 의 `ingest_guard` 가 **`locked`**
- [x] 토큰 없는 `POST /hub/calls` 가 401 이고, 미디에이터를 거친 통화는 정상이다
- [x] 런북 12장(또는 `release.yml`)에 `CORE_API_TOKEN` 단계가 들어갔다 → 12-2-b (09-22)

## 2026-09-22 — ③ 시크릿 주입 완료 (정성윤, Windows 머신에서 SSM)

- 노드 안에서 `openssl rand -hex 32` 로 토큰을 만들어 **미디에이터 시크릿(`CORE_API_TOKEN`) → 롤아웃 → 파드 안 길이 64 확인 → `server-env`(`INGEST_SERVICE_TOKEN`) → 롤아웃** 순서로 넣었다. 토큰 값은 어디에도 찍지 않았다.
- 결과: `/health` **`ingest_guard: locked`** · 토큰 없는 `POST /hub/calls` **401** · 미디에이터 `/health` ok · 파드 넷 재시작 0.
- 시크릿 백업: 노드 `/root/secret-backups/20260921-183422/`(UTC 시각). 되돌리기는 그 두 yaml `apply` + 두 deploy 재시작.
- **아직 안 본 것**: 미디에이터를 거친 실제 통화가 그대로 저장되는지 — 류준 님의 SYN-010 운영 투입(사용자 허용 09-22)이 그 확인이다. 토큰은 정성윤이 SSM 으로 읽어 파일 아닌 방법으로 건넨다.
- 남은 것: ④ 서버 fail-closed 코드(별도 PR, 장민석 님 검토 대상) · 런북 12장에 `CORE_API_TOKEN` 단계(같은 날 추가).

## 결과 (2026-09-22)

③ 시크릿 주입은 끝났다 — 운영 `/health` `ingest_guard: locked`. ④ 서버 fail-closed 코드는 **`w6-ingest-guard-fail-closed`(장민석)** 로 쪼개 넘겼으므로 이 티켓은 닫는다. 「없으면 연다」 분기가 남아 있는 동안 잠금은 시크릿 덕분이지 코드가 지키는 것이 아니다 — 그 티켓이 닫혀야 새 클러스터에서도 안전하다.
