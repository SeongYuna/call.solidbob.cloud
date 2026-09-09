---
title: "AWS 운영 인프라 구축 — EC2 + RDS + Elasticsearch"
assignee: "정성윤"
role: "infra"
status: "in-progress"
sprint: 3
priority: 1
date: 2026-09-03
requirement:
  - "SEC-2"
  - "COST-1"
paths:
  - "infra/terraform/*"
  - "infra/docker/*"
---

## 무엇을

`server`(FastAPI + `ai/` 라이브러리)를 실제 주소에서 돌게 만든다.
지금 `infra/` 에는 **로컬 도커 컴포즈밖에 없고 운영 쪽은 코드 0줄**이다.

클라우드플레어에 `ai`·`server` 레코드가 **apex 를 가리키는 자리표시자**로 남아 있다
([2026-08-28 기록](/progress/)). 이 티켓이 그걸 실제 주소로 바꾼다.

## 구성 — EC2 + RDS 분리, Terraform

| | 무엇 | 왜 |
|---|---|---|
| EC2 | `server` 컨테이너 + Elasticsearch(nori) | 아래 ES 항목 참고 |
| RDS | PostgreSQL 17 | 백업·스냅샷이 딸려 온다. 전사 데이터는 지우면 복구 경로가 없다 |
| Terraform | `infra/terraform/` | `destroy` 로 정리할 수 있어야 크레딧을 태우고도 되돌린다 |

**컨테이너는 하나다** — `ai/` 는 서비스가 아니라 라이브러리라 `main.py` 가 같은 프로세스에서
꽂는다(`_project/decisions/024`). 따라서 도메인도 `server.solidbob.cloud` 하나다.
`CLAUDE.md` 가 적어 둔 `ai.solidbob.cloud` 는 **틀린 서술**이며 이 티켓에서 정리한다
(`_project/decisions/105`) — [미결 항목](/open-items/)에 「정성윤 결정」으로 걸려 있던 건이다.

## ⚠ Elasticsearch 는 관리형을 못 쓴다

Amazon OpenSearch Service 는 **ES 7.10 포크**다. `ai/requirements.txt` 의
`elasticsearch==9.5.0` 클라이언트가 붙지 않는다 — `decisions/020` 이 9.x 클라이언트로
8.15.3 서버에 붙여 보고 이미 겪은 그 에러다.

```
BadRequestError(400, 'media_type_header_exception',
  'Accept version must be either version 8 or 7, but found 9')
```

그래서 `infra/elasticsearch/Dockerfile` 로 굽는 **nori 포함 이미지를 EC2 에서 직접 띄운다.**
RRF 는 어차피 basic 라이선스에서 막혀 우리 코드가 계산한다(`decisions/021`) — 관리형을
포기해서 잃는 기능이 없다.

## 할 것

> **2026-09-03 방향 변경 — 콘솔로 세운다.** Terraform 은 당분간 쓰지 않는다(사용자 지시).
> 절차서: [`infra/aws-console-setup.md`](https://github.com/SeongYuna/call.solidbob.cloud/blob/main/infra/aws-console-setup.md)
> ⚠ **둘을 같이 돌리지 않는다** — Terraform 은 콘솔로 만든 것을 몰라서 리소스가 두 벌 생긴다.

- [x] `infra/aws-console-setup.md` — 콘솔 클릭 절차서(예산→키페어→보안그룹→EC2→EIP→RDS→배포→DNS)
- [x] `infra/terraform/` — 같은 구성의 코드 버전. `terraform validate` 통과. **지금은 설계서로만 쓴다**
- [x] `infra/docker/server.Dockerfile` — `server/` + `ai/apps` 를 한 이미지로
- [x] `infra/docker/compose.prod.yml` · `Caddyfile` — HTTPS 종단(Let's Encrypt 자동 갱신)
- [x] `infra/docker/env.prod.example` — 운영 키 **이름만** (SEC-2)
- [ ] `aws configure --profile callguard` → `terraform apply`
- [ ] 클라우드플레어 `server` 레코드를 EIP 로 · 자리표시자 `ai` 레코드 삭제
- [ ] `db/schema.sql` 을 RDS 에 적용
- [ ] `/health` 가 `spokes` 에 `retrieval` 을 보고하는지 확인

## 2026-09-03 — 설계에서 갈린 것 둘

**① Elasticsearch 를 관리형으로 못 쓴다** (위 참고). EC2 에서 로컬과 **같은 Dockerfile** 로 굽는다.

**② 서버 이미지에 `ai/requirements.txt` 를 넣지 않는다.** 거기엔 `torch`·`transformers` 가 있어
이미지가 수 GB 가 된다. 그런데 요청 경로가 `ai/` 에서 실제로 쓰는 것은 `retrieval` 뿐이고,
그 트리의 서드파티 import 를 전수 확인하니 **`elasticsearch` 하나**였다.
그래서 `server/requirements.txt` + `elasticsearch==9.5.0` 만 설치한다.

⚠ **버전이 두 곳에 손으로 적혀 있다** — `ai/requirements.txt` 와 이 Dockerfile.
어긋나면 ES 서버에 아예 붙지 않는다(`decisions/020` 실측). 한쪽을 올릴 때 다른 쪽도 올린다.

## 완료 조건

`https://server.solidbob.cloud/health` 가 `spokes` 를 실제로 보고하고,
`terraform destroy` → `apply` 로 같은 상태가 다시 선다.

## 하지 않는 것

- **`services/gateway`(A-1 STT)는 이 티켓 밖이다** — 코드가 0줄이라 올릴 것이 없다
- **생성 모델(EXAONE)을 EC2 에 올리지 않는다** — 지금 검색은 BM25 뿐이고,
  모델을 올리는 순간 인스턴스 등급이 한 단계 뛴다. 필요해지면 그때 별도 티켓으로 잰다
