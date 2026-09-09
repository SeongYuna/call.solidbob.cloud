# CLAUDE.md — infra/

**로컬 개발 인프라 + 운영 배포 산출물.** 저장소 전체 규칙은 루트 `../CLAUDE.md` 가 우선하고,
이 파일은 그 아래에서 `infra/` 와 AWS 운영 환경의 일만 다룬다.

- 로컬 사용법(compose·ES nori 이미지) → `README.md`
- **운영(AWS)은 `../docs/infra-runbook.md` 가 정본이다.** 이 파일은 그 런북을 규칙으로 번역한 것이고,
  둘이 어긋나면 **런북이 맞다**(루트 §1 문서 우선순위 — 파생 문서는 3위).

담당: **정성윤**(AWS·인프라·CI 운영). 다른 사람이 여기를 고칠 일이 생기면 먼저 말로 맞춘다.

---

## 0. 무엇을 먼저 읽는가

| 하려는 일 | 런북에서 읽을 곳 |
|---|---|
| AWS 자원을 만들거나 바꾼다 | 1~8장 + **「만들지 말 것」** |
| k3s 위에 무엇을 올린다 | 10~16장 (**11장 GPU 공유가 가장 실수하기 쉽다**) |
| 배포됐는지 확인한다 | 19장 검증 체크리스트 9개 |
| 비용이 걱정된다 | 0장(자원·비용) · 21장(자동 중지가 예산을 결정한다) |
| 막혀서 되돌린다 | 「되돌리기 · 정리」 — **compose 경로를 지우지 않는다** |
| 왜 이 구성인지 설명해야 한다 | 부록 A (EKS 대신 k3s · 통합 노드 · 버스터블 회피) |

---

## 1. 절대 지킬 것 (런북 「만들지 말 것」 · 부록 B)

1. **GPU 인스턴스를 24/7 로 켜지 않는다.** 6주 $142 → $597 로 예산을 넘긴다.
   21-1 의 자동 중지(`0 2 * * * shutdown -h now`)를 끄지 않는다.
2. **NAT Gateway · EKS · ALB/NLB · Kinesis · ElastiCache · Multi-AZ RDS · 직접 만든 VPC 를 만들지 않는다.**
   각각의 대안이 런북에 적혀 있다. Kinesis 는 비용보다 **통제 불가 지연 구간이 느는 것**이 문제다(10.7절).
3. **NVIDIA device plugin 을 설치하지 않는다.** `nvidia.com/gpu` 를 요청하는 순간 파드 하나만 GPU 를 받고
   나머지는 영원히 `Pending` 이다. **RuntimeClass 만** 쓴다(11장).
4. **Ollama(11434) · Elasticsearch(9200)를 인터넷에 열지 않는다.** 둘 다 인증이 없다 — ClusterIP 로만 접근한다.
   k3s API(6443)와 SSH(22)는 **내 IP 로만** 연다.
5. **자격증명을 커밋하지 않는다**(SEC-2, 루트 §8). RDS 암호·엔드포인트는 k8s 시크릿 `db-credentials` 로만 들어가고,
   EC2 는 액세스 키가 아니라 IAM 역할(`assist-ec2-role`)로 S3 에 접근한다.
6. **19장을 통과하면 즉시 AMI 를 만든다**(20장). 재세팅에 반나절이 든다.

---

## 2. 로컬과 운영이 다른 지점

| | 로컬 (`docker-compose.yml`) | 운영 (런북) |
|---|---|---|
| DB | 컨테이너 PostgreSQL 17, `db/schema.sql` 자동 적용 | RDS `assist-pg`, 스키마는 **17장에서 수동 적용** |
| ES | 힙 512m, `127.0.0.1` 바인딩 | 힙 2g, ClusterIP(외부 비공개) |
| 이미지 | `docker compose build` | `docker save … \| k3s ctr images import` + `imagePullPolicy: Never` (13-1) |
| 설정 | 루트 `.env` | k8s 시크릿 + 파드 `env` (12-2 · 16-1) |

**운영 배포 산출물의 경로를 런북이 전제한다** — `infra/docker/server.Dockerfile` · `infra/docker/Caddyfile` ·
`infra/elasticsearch/`. 옮기면 런북 13·16장을 함께 고친다.

---

## 3. 아직 없는 것 (2026-09-04 확인)

런북이 참조하지만 저장소에 없다. 만들 때 **런북이 적은 경로 그대로** 만든다.

- `infra/docker/server.Dockerfile` · `infra/docker/Caddyfile` (13-1 · 16-2)
- `infra/docker/compose.prod.yml` · `env.prod.example` (「되돌리기」 후퇴 경로)
- **부록 B 의 결정 기록 9건** — `_project/decisions/1xx`(정성윤 번호대, 루트 §4).
  런북 18장이 이미 `decisions/103`(Cloudflare 프록시 금지)을 참조하지만 파일이 없다.
- 런북 13장의 클론 주소가 `github.com/SeongYuna/…` 인데 루트 문서·원격은 `github.com/solidbob02/…` 다 — 한쪽으로 맞춘다.
