# infra/

배포와 로컬 개발 환경. **2026-09-08 부터 도커 컴포즈를 쓰지 않는다** — 운영은 EC2 + k3s,
로컬은 `docker run` 두 줄이다. 경위·되돌리는 법: `_project/decisions/107`.

```
infra/
├── docker/
│   ├── server.Dockerfile   server(FastAPI) + ai/apps 를 한 이미지로
│   └── gateway.Dockerfile  services/gateway(Node.js) — 따로 굽고 따로 뜬다 (2026-09-11)
├── elasticsearch/
│   └── Dockerfile          공식 ES 이미지 + nori 형태소 분석기
└── k8s/
    ├── base/               운영(EC2)에 실제로 떠 있는 구성
    └── local/              로컬 k3s 리허설 오버레이 (Ingress·STT 키 제외 · ES 힙 축소)
```

> ⚠ 운영(AWS) 인프라는 정성윤 담당이다([7.1절](/docs/07/)). 콘솔 절차·비용·자동 중지는
> 별도 개인 운영 문서(`AWS 인프라 구축·운영 지침서`)에 있고, 저장소에 두지 않는다 —
> 계정·키·RDS 자격증명이 섞이기 때문이다(SEC-2, CLAUDE.md §8).

## 이미지 굽기

**둘 다 저장소 루트에서, 로컬에서 굽고 Docker Hub 로 올린다.** EC2 는 pull 만 한다.

```bash
# server — 컨텍스트가 저장소 루트여야 한다 (아래 참고)
docker buildx build --platform linux/amd64 \
  -f infra/docker/server.Dockerfile \
  -t seongyuna/callguard-server:0.1.0 --push .

# Elasticsearch — nori 포함
docker buildx build --platform linux/amd64 \
  -t seongyuna/callguard-es:9.5.1 --push infra/elasticsearch/
```

지켜야 할 것 셋 —

- **`--platform linux/amd64`.** EC2 가 x86_64 다. arm64 로 구우면 `exec format error` 로 죽는데
  로컬에서는 멀쩡해서 원인을 찾기 어렵다.
- **컨텍스트는 저장소 루트(`.`).** `main.py` 가 `../ai/apps` 를 경로에 올려 검색 스포크를 꽂는다.
  `server/` 만 넣으면 서버는 뜨는데 `/health` 의 `spokes` 에서 `retrieval` 이 조용히 빠진다.
- **`latest` 를 쓰지 않는다.** k3s 가 캐시된 이미지를 계속 쓴다. `0.1.0` → `0.1.1` 로 올린다.

### 이미지에 무엇이 들어가는가

`server/requirements.txt` **+ `elasticsearch` 하나**다. `ai/requirements.txt` 전체를 넣지 않는다 —
거기엔 `torch`·`transformers` 가 있어 이미지가 수 GB 가 되는데, 요청 경로가 `ai/` 에서 실제로
쓰는 서드파티는 `elasticsearch` 뿐이다. **실측 362MB.**

버전은 Dockerfile 에 손으로 적지 않고 `ai/requirements.txt` 에서 뽑는다. 두 곳에 적으면
어긋나고, 어긋나면 ES 서버에 아예 붙지 않는다(`decisions/020`).

### 확인

```bash
docker run --rm -p 8000:8000 \
  -e ELASTICSEARCH_URL=http://elasticsearch:9200 \
  -e DATABASE_URL=postgresql://callguard:<암호>@<호스트>:5432/callguard \
  seongyuna/callguard-server:0.1.0

curl -s localhost:8000/health
# {"status":"ok","postgres_configured":true,"elasticsearch_configured":true,
#  "spokes":["masking","closure_gate","retrieval"]}
```

**`spokes` 에 `retrieval` 이 있어야 검색이 꽂힌 것이다.** 없으면 `ELASTICSEARCH_URL` 이 안 잡혔거나
`ai/apps` 가 이미지에 안 들어간 것이다. 서버 자체는 정상으로 뜨므로 여기서만 드러난다
(`decisions/024` — 못 꽂으면 조용히 501 로 남는 것이 설계된 동작이다).

Swagger 는 FastAPI 가 자동으로 준다 — `http://localhost:8000/docs`.

## k3s 배포

**PostgreSQL 은 클러스터 안에 없다.** RDS 를 독립적으로 쓰고, 접속 정보만 시크릿으로 넣는다.

```bash
# 1) cert-manager — 클러스터에 한 번만
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml
kubectl wait --for=condition=Available -n cert-manager deploy --all --timeout=180s
#    base/clusterissuer.example.yaml 의 이메일을 채워 apply

# 2) 자격증명 2개 — 저장소에 넣지 않는다 (SEC-2). base/secret.example.yaml 참고
kubectl create namespace callguard
kubectl create secret generic server-env -n callguard --from-env-file=.env
kubectl create secret generic gcp-stt-credentials -n callguard --from-file=<키파일>.json

# 3) 배포
kubectl apply -k infra/k8s/base/

# 4) 확인
kubectl -n callguard get pods
curl -s https://server.solidbob.cloud/health
```

### 저장소와 클러스터가 어긋나지 않았는지

```bash
kubectl kustomize infra/k8s/base/ | ssh <EC2> 'kubectl diff -f -'
```

**아무것도 안 나오면 일치한다**(종료코드 0). 손으로 클러스터를 고쳤다면 여기서 드러난다 —
그때는 저장소를 고쳐 맞춘다. 클러스터만 아는 구성은 인스턴스가 사라질 때 같이 사라진다.

`kubectl create secret` 을 **먼저** 한다. `callguard-server` 는 `envFrom.secretRef` 로 받으므로
시크릿이 없으면 파드가 뜨지 않는다 — `optional: true` 로 두면 `postgres_configured=false`
인 채 조용히 떠서 문제를 늦게 발견한다.

⚠ **`.env` 가 최신인지 먼저 본다.** 2026-09-08 에 `MYSQL_*` → `POSTGRES_*` 로 고쳤다
(`decisions/107`). 옛 파일을 넣으면 서버는 정상으로 뜨는데 `/health` 만 `false` 를 뱉는다.

이미지 태그를 올릴 때는 `infra/k8s/base/kustomization.yaml` 의 `images:` 한 곳만 고친다.
급하면 `kubectl -n callguard set image deploy/server server=seongyuna/callguard-server:0.1.1`
도 되지만, 그러면 저장소와 클러스터가 어긋난다.

> ⚠ **k3s 내장 Traefik 을 끄지 않는다.** Ingress 가 Traefik 을 쓰고, cert-manager 가
> 그 위에서 HTTP-01 챌린지로 인증서를 받는다. `--disable=traefik` 로 설치하면 안 된다.
> ⚠ **Elasticsearch 는 ClusterIP 로만 둔다.** `xpack.security` 를 껐으므로 NodePort·Ingress 로
> 열면 인증 없는 데이터 저장소가 공개된다.

### 로컬 k3s 리허설

EC2 에 올리기 전에 같은 매니페스트를 노트북에서 돌려 본다.

```bash
kubectl apply -k infra/k8s/local/
kubectl create secret generic server-env -n callguard \
  --from-literal=DATABASE_URL='postgresql://callguard:local@localhost:5432/callguard' \
  --from-literal=ELASTICSEARCH_URL='http://elasticsearch:9200'

kubectl -n callguard exec statefulset/elasticsearch -- curl -s http://callguard-server/health
kubectl -n callguard port-forward svc/callguard-server 8000:80   # → http://localhost:8000/docs
```

운영과 다른 점은 셋뿐이다 — Ingress 를 빼고(로컬엔 도메인·인증서·cert-manager 가 없다),
ES 힙을 512m 으로 낮추고, Google STT 키 볼륨을 뺀다(그 시크릿이 로컬엔 없다).
이미지·이름·포트·envFrom·프로브는 **같은 것**을 쓴다.

## 로컬 개발 (컴포즈 대체)

`docker compose up -d` 대신 두 줄이다. **PostgreSQL 과 Elasticsearch 만 띄우고, server 는
평소대로 `uvicorn --reload` 로 돌린다** — 코드를 고칠 때마다 이미지를 다시 굽지 않는다.

```bash
# PostgreSQL — db/schema.sql 을 최초 기동에 한 번 적용한다
docker run -d --name callguard-postgres \
  -e POSTGRES_DB=callguard -e POSTGRES_USER=callguard -e POSTGRES_PASSWORD=callguard-dev \
  -e POSTGRES_INITDB_ARGS="--encoding=UTF8 --locale=C" -e TZ=Asia/Seoul \
  -p 5432:5432 -v callguard-pg:/var/lib/postgresql/data \
  -v "$PWD/db/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql:ro" \
  postgres:17

# Elasticsearch — nori 이미지를 먼저 굽는다 (최초 1회 몇 분)
docker build -t callguard-es:local infra/elasticsearch/
docker run -d --name callguard-elasticsearch \
  -e discovery.type=single-node -e xpack.security.enabled=false \
  -e ES_JAVA_OPTS="-Xms512m -Xmx512m" -e ingest.geoip.downloader.enabled=false \
  -p 127.0.0.1:9200:9200 -v callguard-es:/usr/share/elasticsearch/data \
  callguard-es:local
```

**ES 포트를 `127.0.0.1` 에만 바인딩한다** — 로컬이라 `xpack.security` 를 껐다. 인증 없는 ES 를
외부에 열지 않는다. 같은 이유로 k3s 에서도 ES 는 ClusterIP 로만 둔다.

정지·삭제:

```bash
docker stop callguard-postgres callguard-elasticsearch
docker rm   callguard-postgres callguard-elasticsearch
docker volume rm callguard-pg callguard-es    # 데이터까지 지울 때 (스키마 재적용)
```

### `.env` 에 넣을 값

```
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB_NAME=callguard
POSTGRES_USER=callguard
POSTGRES_PASSWORD=callguard-dev
DATABASE_URL=postgresql://callguard:callguard-dev@127.0.0.1:5432/callguard
ELASTICSEARCH_URL=http://127.0.0.1:9200
```

**`.env` 는 커밋되지 않는다**(SEC-2). 키 이름은 `.env.example` 과 1:1 이다.

### 확인

```bash
docker exec callguard-postgres psql -U callguard -d callguard -c '\dt'
curl localhost:9200/_cat/plugins            # analysis-nori 가 보여야 한다
curl -X POST localhost:9200/_analyze -H 'Content-Type: application/json' \
  -d '{"analyzer":"nori","text":"전입신고에 필요한 서류를 알려주세요"}'
```

## Elasticsearch 버전을 바꿀 때

**`9.5.1` 이다.** `ai/requirements.txt` 의 `elasticsearch==9.5.0` 클라이언트와 major·minor 를
맞춘 값이다. 어긋나면 붙지 않는다 — 9.x 클라이언트로 8.15.3 서버에 붙여 본 결과:

```
BadRequestError(400, 'media_type_header_exception',
  'Accept version must be either version 8 or 7, but found 9')
```

한쪽을 바꾸면 다른 쪽도 바꾼다. 근거: `_project/decisions/020`.

> ⚠ **RRF 는 basic 라이선스에서 막힌다.** `retriever.rrf` 는 8.15.3·9.5.1 **양쪽 다**
> `403 current license is non-compliant` 로 거부된다(실측). 30일 trial 은 2026-09-26 에
> 만료돼 프로젝트 종료(10-27)를 못 넘긴다. 순위 병합은 `ai/` 검색 코드에서 계산한다
> (`decisions/021`). **BM25·kNN·nori·`dense_vector` 자체는 basic 에서 전부 된다.**

## 스키마를 고쳤을 때

`db/schema.sql` 은 **최초 기동(빈 볼륨)일 때만** 적용된다. 로컬은 볼륨을 지우고 다시 띄운다.
운영(RDS)은 클러스터 안에서 `kubectl run psql` 로 적용한다 — 퍼블릭 액세스가 없기 때문이다.
스키마 변경은 [팀 승인 사안](/backlog/w1-db-schema/)이다.
