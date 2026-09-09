---
title: "컴포즈를 걷어내고 k3s 배포 준비 — 이미지 2종·Caddy·로컬 대체"
assignee: "정성윤"
role: "infra"
status: "in-progress"
sprint: 3
priority: 2
date: 2026-09-08
depends_on:
  - "w3-aws-deploy"
paths:
  - "infra/docker/*"
  - "infra/elasticsearch/*"
  - "infra/k8s/*"
---

## 무엇을

`infra/docker-compose.yml` 을 삭제하고, EC2 + k3s 배포에 필요한 것을 저장소에 넣는다.
결정·근거: `_project/decisions/107`.

## 왜

`w3-aws-deploy` 가 `infra/docker/server.Dockerfile` 을 `[x]` 로 적어 두었으나
**git 이력 전수 확인 결과 커밋된 적이 없다.** `infra/terraform/`·`infra/aws-console-setup.md`
도 마찬가지다. 실제로 있던 것은 `infra/elasticsearch/Dockerfile` 하나였고, 그것마저
컴포즈를 지우면서 함께 삭제된 상태였다. **이게 없으면 배포 첫 단계에서 막힌다.**

## 완료 조건

- [x] `infra/elasticsearch/Dockerfile` 복구 (nori 이미지를 굽는 유일한 파일)
- [x] `infra/docker/server.Dockerfile` — `server/` + `ai/apps` 를 한 이미지로
- [x] ~~Caddyfile~~ → **폐기.** 실제 EC2 는 k3s 내장 Traefik + cert-manager 로 갔다.
      `infra/k8s/base/ingress.yaml` 이 그 자리를 대신한다 (`decisions/107` 정정 항목)
- [x] `.dockerignore` — 컨텍스트가 저장소 루트라 `.env`·`data/` 가 딸려 들어갈 수 있었다(SEC-2)
- [x] `.env` 를 `MYSQL_*` → `POSTGRES_*` 로, `POSTGRES_PORT` `3306` → `5432`
- [x] `infra/README.md` — 컴포즈 삭제 + 로컬 `docker run` 대체 절차
- [x] **로컬 실측** — 이미지 362MB, `/docs` 200, `/health` 의 `spokes` 에 `retrieval` 확인
- [x] Docker Hub push — `seongyuna/callguard-server:0.1.0`(362MB) · `seongyuna/callguard-es:9.5.1`(2.58GB), 둘 다 public
- [x] **nori 실동작 확인** — `_cat/plugins` 에 `analysis-nori 9.5.1`, `_analyze` 가 「전입신고에」를 `전입·신고`로 쪼갠다
- [x] `infra/k8s/` 매니페스트 — `base/`(운영) + `local/`(리허설). kustomize
- [x] **로컬 k3s 리허설 통과** — 파드 2개 Running, 클러스터 안에서 `/health` 의 `spokes` 에 `retrieval`
- [x] 컴포즈를 가리키던 살아 있는 문서 3곳 정리 (`README.md` · `scripts/index_knowledge_base.py` · `docs/06`)
- [x] `infra/docker-compose.yml` 삭제를 커밋에 포함 (2026-09-09)
- [x] 류준·장민석에게 로컬 환경 변경 통보 (2026-09-09)
- [x] **EC2 배포 완료 (2026-09-08)** — Amazon Linux 2023 · k3s v1.36.4 · Traefik Ingress + cert-manager
- [x] `https://server.solidbob.cloud/health` 가 `spokes:[masking,closure_gate,retrieval]` 보고, Let's Encrypt 인증서 정상
- [x] **매니페스트를 실제 구성에 맞춰 재작성** — `kubectl diff` 로 클러스터와 **차이 0** 확인
- [ ] ES 인덱스 적재 (`scripts/index_knowledge_base.py --to-es --recreate`) — 없으면 `/hub/search` 가 500
- [ ] **AMI 스냅샷** — 지금 구성이 EC2 안에만 있다
- [ ] 자동 중지 cron (지침서 21-1)

## 실측 (2026-09-08, 로컬)

```
docker build -f infra/docker/server.Dockerfile -t callguard-server:test .   → 362MB
docker run -e ELASTICSEARCH_URL=... -e DATABASE_URL=... callguard-server:test
GET /health  → {"status":"ok","postgres_configured":true,
                "elasticsearch_configured":true,
                "spokes":["masking","closure_gate","retrieval"]}
GET /docs    → 200   (Swagger, 경로 13개)
```

`spokes` 의 `retrieval` 이 **빌드 컨텍스트가 저장소 루트인지**를 재는 지표다. `server/` 만
넣으면 여기서만 드러나고 서버는 정상으로 뜬다(`decisions/024`).

## 남은 것

k3s 매니페스트(Deployment·Service·PVC·Secret)는 개인 운영 지침서에 인라인으로 있다.
저장소에 `infra/k8s/` 로 옮길지는 **자격증명이 섞이지 않는 범위에서** 따로 정한다 —
지침서 자체는 계정·키가 들어 있어 저장소에 두지 않는다(SEC-2, CLAUDE.md §8).
