---
title: "배포 확인용 프로브 — GET /admin/auth/test"
assignee: "정성윤"
role: "infra"
status: "in-progress"
sprint: 4
priority: 6
date: 2026-09-15
requirement:
  - "관리자 로그인(구글)"
paths:
  - "server/apps/admin_auth/adapter/inbound/api/v1/auth_router.py"
  - "infra/k8s/base/kustomization.yaml"
---

## 무엇을

`server/` 를 고쳐 main 에 머지하면 **운영의 `/docs`·`/openapi.json` 이 실제로 바뀌는가**를
눈으로 확인한다. 인증·DB·Redis 를 타지 않는 엔드포인트 하나(`GET /admin/auth/test`)를 넣고,
이미지 태그를 올려(`0.1.6` → `0.1.7`) 릴리스 → k3s 적용 → 스웨거 대조까지 한 번 완주한다.

## 왜

「머지 = 배포」가 **서버 쪽에서** 실제로 도는지 끝까지 본 적이 없다. `release.yml` 의 `paths`
필터·태그 게이트·SSM 적용·스모크 테스트가 줄줄이 걸려 있어서, 조용히 안 도는 구간이 있어도
`/health` 는 그대로 `ok` 다 — 09-08~09-11 운영 DB 사고를 사흘간 가린 것이 바로 그 `ok` 였다
(`decisions/108`). 프론트(Vercel)의 자동 배포가 도는지도 아직 안 봤다([미결](/open-items/)).

## 완료 조건

- [x] `GET /admin/auth/test` — 200 · 응답 말단 전부 문자열 · 비밀 없음(SEC-2)
- [x] `/openapi.json` 공표까지 검증하는 테스트 3건 (`test_auth_probe_router.py`)
- [x] `kustomization.yaml` `newTag` 0.1.6 → 0.1.7 (`check_release_tags.py` 통과)
- [ ] main 머지 후 `curl https://server.solidbob.cloud/openapi.json` 에 경로가 **보인다**
- [ ] 확인이 끝나면 프로브를 걷어낸다 (아래)

## 걷어낼 때

`auth_router.py` 의 `probe`·`PROBE_MARKER`, `auth_schema.py` 의 `AuthProbeResponse`,
`tests/test_auth_probe_router.py`, 이 티켓, 미결 항목 한 줄 — 다섯 곳이다.
**걷어낼 때도 `newTag` 를 올린다.**
