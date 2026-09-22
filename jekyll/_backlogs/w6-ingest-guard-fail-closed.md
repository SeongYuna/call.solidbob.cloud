---
title: "서비스 토큰이 없으면 쓰기 문이 열리지 않게 — ingest_guard fail-closed"
assignee: "장민석"
role: "ai"
status: "todo"
sprint: 6
priority: 60
date: 2026-09-22
requirement:
  - "SEC-2"
depends_on:
  - "w5-ingest-auth-fail-closed"
paths:
  - "server/apps/hub/dependencies/ingest_guard.py"
  - "server/core/config.py"
---

> **정성윤이 09-22 오늘 진행 기록·미결 항목을 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

`server/apps/hub/dependencies/ingest_guard.py` 의 `require_ingest_service` 는 **토큰이 설정돼 있을 때만 요구하고, 없으면 통과**시킨다.
`decisions/120` 「전환 순서」 4번 — 미디에이터가 토큰을 보내기 시작하면 fail-closed 로 바꾼다. 그 전환은 09-22 오전에 끝났다(`ingest_guard: locked`).

## 왜

- 시크릿을 되돌리거나 키를 빠뜨리면 서버는 멀쩡히 뜨고 문만 조용히 열린다 — 09-20 이전 상태. `/health` 에 `open` 이 찍히지만 사람이 봐야 안다
- 새 클러스터는 `release.yml` 이 이 토큰을 만들지 않아 기본이 열림이다. 서버가 안 뜨면 잊을 수 없다
- 업로드 문(`110`)과 `/close`(`315`)는 이미 「없으면 잠금」 — 이 문만 반대다

## 완료 조건

- [ ] 토큰 미설정이면 쓰기 일곱 경로가 **401**(또는 기동 거부). 테스트: 없음 401 · 틀림 401 · 맞음 200
- [ ] `config.py`·`ingest_guard.py` 의 「이행기」 주석 정리 · 런북 12-2-b 에 「없으면 서버가 안 뜬다/닫힌다」 한 줄
- [ ] 태그 올림 · 배포 뒤 `/health` 가 여전히 `locked`
