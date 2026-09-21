---
title: "쓰기 경로 인증 3·4단계 — 시크릿 주입 → 서버 fail-closed"
assignee: "정성윤"
role: "infra"
status: "todo"
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
- [ ] `server-env` 에 같은 값 주입 → `/health` 의 `ingest_guard` 가 **`locked`**
- [ ] 토큰 없는 `POST /hub/calls` 가 401 이고, 미디에이터를 거친 통화는 정상이다
- [ ] 런북 12장(또는 `release.yml`)에 `CORE_API_TOKEN` 단계가 들어갔다
