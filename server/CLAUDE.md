# CLAUDE.md — server/

**요청이 흐르는 길.** 계약(포트·DTO)을 정의하고 파이프라인을 배선한다.
저장소 전체 규칙은 루트 `../CLAUDE.md` 가 우선하고, 이 파일은 그 아래에서 `server/` 안의 일만 다룬다.

배포 대상: `server.solidbob.cloud`

---

## 0. 이 디렉터리가 하는 일 / 하지 않는 일

| | |
|---|---|
| **한다** | 계약 정의(포트·DTO) · 파이프라인 배선 · 클린 아키텍처 유지 · HTTP 경계 · 설정·비밀 관리 · 저장(DB) |
| **하지 않는다** | 모델 학습 · 청킹 · BM25 · 리랭크 · 임베딩 · 랭그래프/랭체인 오케스트레이션 · 평가 채점 |

위쪽이 `server/`, 아래쪽이 `../ai/` 다. **경계가 헷갈리면 이렇게 판단한다.**

```
"요청 하나를 처리하는 데 반드시 실행되는가?"   → 예: server/
"품질을 만들거나 재는 코드인가?"              → 예: ai/
```

C-5 마스킹·F-2 종결 게이트처럼 **규칙 기반 판정**은 요청 경로에서 매번 실행되므로 `server/` 다.
"판정은 규칙이, 설명만 LLM이 한다"(루트 절대 원칙 9)를 배치로 고정한 것이다.

---

## 1. 의존 방향 — 한쪽뿐이다

```
ai/  ──(hub 포트·DTO를 import)──▶  server/
server/  ──✗──▶  ai/            (금지)
```

`hub` 가 포트(추상)를 정의하고 `ai/` 쪽 모듈이 그것을 구현한다.
**`server/` 가 `ai/` 를 import 하는 순간 두 서브도메인이 한 덩어리가 되어 따로 배포할 수 없다.**
구체 구현은 실행 시점에 어댑터로 주입한다(`apps/hub/dependencies/`).

`.importlinter` 계약 2 가 이것을 강제한다 — `torch`·`transformers`·`langchain`·`langgraph` 도 함께 금지 목록에 있다.
서버 컨테이너에 그것들이 들어오면 방향이 이미 무너진 것이다.

---

## 2. 구조

```
server/
  main.py               합성 루트. sys.path 에 apps/ 를 올리고 라우터를 붙인다
  core/config.py        os.environ 을 읽는 유일한 곳 (.env.example 키와 1:1)
  apps/hub/             허브 — 계약과 수직 슬라이스
    app/dtos/           계약 DTO (7.3절 v2)
    app/ports/input/    유스케이스 인터페이스
    app/ports/output/   스포크가 구현할 포트 (retrieval·masking·trigger·compliance·closure_gate·domain_routing·generation)
    app/use_cases/      인터랙터 — 판정 없이 배선만
    adapter/inbound/    라우터 · 요청/응답 스키마
    adapter/outbound/   기록 어댑터
    dependencies/       구체 구현 주입 지점
    tests/
  tests/                main.py(합성 루트) 전용
```

**수직 슬라이스는 프랙탈이다.** 슬라이스 하나를 추가할 때
`schema → router → dto → input port → interactor → output port → adapter → provider → test`
단면을 전부 만든다. 한 층만 만들고 넘어가면 다음 사람이 나머지를 찾아 헤맨다.

기존 예시: `transcript_ingest`(전사 수신) · `myself`(헬스/자기소개).

---

## 3. 절대 지킬 것

1. **마스킹 없는 임시 통과 경로를 만들지 않는다.** `POST /hub/transcripts` 는 masking 스포크가
   등록되지 않으면 **501** 을 반환한다. "일단 동작하게" 하려고 원문을 통과시키면 SEC-1 위반이고,
   그 임시 코드는 반드시 남는다.
2. **인터랙터는 판정하지 않는다.** 종결 가능 여부·요건 충족·마스킹 대상 판정을 유스케이스 안에서
   if 문으로 쓰지 않는다. 규칙 모듈(포트 뒤)에 맡기고 결과만 배선한다.
3. **`os.environ` 은 `core/config.py` 에서만 읽는다.** 다른 곳에서 읽으면 무엇이 필요한 설정인지
   추적이 끊긴다. `/health` 는 값이 아니라 **설정 여부만** 노출한다(SEC-2).
4. **DTO 안에 판정 로직을 넣지 않는다.** DTO 는 모양이지 규칙이 아니다.
5. **UI 에 위험도 점수나 "안전합니다" 류 표현이 나가는 응답을 만들지 않는다** (부록 A-1).

---

## 4. 검증

```bash
cd server && pytest                            # 단위 테스트
cd server && PYTHONPATH=apps lint-imports --config .importlinter   # 구조 계약 3종
```

CI(`.github/workflows/test.yml`)의 `server` job 이 이 둘을 돌린다.

**실제 PostgreSQL 이 필요한 테스트**(`@pytest.mark.integration`)도 같은 job 이 돈다(2026-09-11) —
매번 새로 띄운 `postgres:17` 에 현재 `../db/schema.sql` 을 넣고 `pytest -m integration`.
DB 는 `conftest.py` 의 `integration_settings` 픽스처로 받는다. 로컬에서는:

```bash
CALLGUARD_TEST_DATABASE_URL=postgresql://…/<새 DB> pytest -m integration   # 현재 schema.sql 을 넣은 DB
```

변수를 안 주면 **스킵한다 — 루트 `.env` 의 DB 는 쓰지 않는다.** 이 테스트들은 행을 쓰고 지우는데
`.env` 의 DB 는 공유·운영 DB 일 수 있다. **가짜 커서 테스트는 SQL 이 스키마와 맞는지 못 본다** —
PK·FK·`ON CONFLICT` 를 건드리면 integration 을 같이 돌린다.
**job 이름은 main 브랜치 보호의 필수 통과 검사 이름이다** — 바꾸면 보호 설정이 조용히 무력화된다.

새 스포크를 만들면 `.importlinter` 의 `root_packages` 와 계약 1 `containers` 에 이름을 추가한다.
아직 없는 패키지를 적으면 `lint-imports` 가 "모듈 없음"으로 실패한다 — 실제로 만든 것만 적는다.

---

## 5. 주 담당 — 장민석 (잠금 아님)

`server/` 는 **장민석**이 주로 본다 — 파이프라인 배선·클린 아키텍처·계약(포트·DTO).
브랜치도 같은 이름 `server` 다(`_project/decisions/015`).

> ⚠ **주 담당이지 전담이 아니다 (2026-09-10, `_project/decisions/302`).**
> **`server/`·`../ai/`·`../infra/` 는 정성윤·류준·장민석 누구나 고친다.** 기능 하나가
> 세 디렉터리에 걸치는데 담당이 갈려 **호출부만 있고 구현체가 없는 구멍**이 남았기 때문이다.
> `../ai/` 를 여기서 같이 고치고 한 PR 로 넣어도 된다.
> **전담이 남는 곳은 프론트엔드(`../apps/`, 조서희) 하나뿐이다.**
> `decisions/012` 의 **역할 구분과 의존 방향(`ai → server`)은 그대로다** — 위 1~4절의
> 경계 판단 기준은 «누가 고치는가» 가 아니라 «무엇이 어디에 들어가는가» 이므로 유효하다.

**`apps/masking/`(C-5)도 장민석이다** — 원래 정성윤 담당이었으나 티켓·코드가 없는 착수 전
상태였고 부재가 겹쳐 2026-08-27 이관했다(`_project/decisions/019`). 게이트웨이·인프라·CI
운영은 정성윤 몫으로 그대로다. ⚠ 정성윤 복귀 시 이 항목을 먼저 공유한다.

`server/` 를 고치면 `ai/` 의 계약 소비 지점이 함께 깨질 수 있다.
**포트·DTO 를 바꿀 때는 `../ai/` 를 먼저 grep 해서 무엇이 깨지는지 확인한다.**

합의를 절차로 요구하지는 않는다(2026-08-27, `_project/decisions/023`). 네 사람이 **같은 공간에서
일하므로 필요하면 그 자리에서 말로 맞춘다.** 규칙이 할 일은 "무엇이 깨지는지 먼저 보라"까지다.

---

## 6. 배포 전제 — `../docs/infra-runbook.md`

운영은 **단일 g4dn.xlarge + k3s**(AWS 서울, 담당 정성윤)다. 로컬에서 도는 것과 거기서 뜨는 것은 다르다.
**파이프라인 배선·설정·HTTP 경계를 고칠 때는 런북 12·16·19장을 먼저 읽는다.**
클러스터에 실제로 떠 있는 구성의 정본은 `../infra/k8s/base/` 다 — 네임스페이스 `callguard` ·
Deployment `callguard-server` · 시크릿 `server-env` (런북 머리말, 2026-09-11).

| 런북 | `server/` 가 지켜야 하는 것 |
|---|---|
| 12-2 | 설정은 k8s 시크릿 **`server-env`** 로 `.env` 키 전체가 들어온다(`server.yaml` `envFrom`). DB 는 **`DATABASE_URL` 과 `POSTGRES_*` 둘 다 같은 RDS 값**이다 — 이미지 `0.1.1` 은 `POSTGRES_*` 만, `0.1.2` 부터는 `DATABASE_URL` 을 먼저 읽는다. 둘이 다른 값을 가리켜 운영 DB 가 09-08~09-11 한 번도 안 붙었다(`decisions/108`). **커넥션 코드와 `/health` 가 같은 규칙으로 키를 읽게 유지한다.** RDS 는 SSL 강제라 URL 에 `?sslmode=require` 가 붙는다 |
| 16-1 | `core/config.py` 가 읽는 키는 `server-env` 에 있어야 한다(`../infra/k8s/base/secret.example.yaml` 이 키 목록). ES 는 같은 네임스페이스의 `http://elasticsearch:9200`. **읽는 키를 새로 만들면 `secret.example.yaml` 과 운영 시크릿에 같이 넣지 않는 한 배포가 조용히 기본값으로 뜬다** |
| 16-1 | 의존 서비스 주소는 호스트가 아니라 **같은 네임스페이스의 서비스 이름**이다. `localhost:9200` 을 기본값으로 굳히지 않는다 |
| 19 | `GET /health` 의 **`spokes` 배열이 배포 검증 항목**이다(9번). 필드 이름·형태를 바꾸면 런북 19장이 깨진다. 스포크가 안 꽂히면 조용히 501 로 남는 것이 설계된 동작이다(`decisions/024`). ⚠ `postgres_configured` 는 설정 **여부**일 뿐이다 — DB 가 붙었는지는 10번(`GET /hub/knowledge-gaps`)·11번(통화 → 전사 → 조회)이 본다. **이 두 엔드포인트의 경로·순서를 바꾸면 19장을 같이 고친다** |
| 16-2 | 외부에 열리는 것은 Caddy 를 지나는 `server.solidbob.cloud` **443 하나**다. 새 포트가 필요한 설계는 인프라 변경이므로 정성윤과 함께 정한다 |
| 만들지 말 것 | Kinesis·ElastiCache·ALB 를 전제한 코드를 쓰지 않는다. 캐시는 3.1절대로 **인메모리 LRU** 다 |

> ⚠ **`../.env.example` 에 `OLLAMA_URL`·`HF_HOME` 키가 없다**(2026-09-04 확인). 런북 16-1 은 둘을 주입한다.
> `.env.example` 은 자격증명 보호 훅(`protect-files.sh`)이 편집을 막으므로 사람이 직접 채운다 — SEC-2 체크리스트 항목이다.
