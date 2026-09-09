# 하네스(Harness) — 구조 무결성

> 카파시式 하네스 엔지니어링: 코드·문서 구조가 올바르게 유지되도록 정적 분석·제약을
> 배선(harness)처럼 엮어 자동으로 검증한다. 사람 리뷰가 놓치는 구조 위반을 **실패**로 만든다.
> 문서는 강제 가능한 규칙만 담고, 강제 수단(명령)을 함께 적는다. 강제 수단이 없는 규칙은 규칙이 아니라 희망이다.

이 저장소에는 "하네스"라는 말이 쓰이는 곳이 셋 있다. 서로 다른 질문에 답한다.

| 하네스 | 답하는 질문 | 위치 | 강제 수단 |
|---|---|---|---|
| 요구사항 하네스 | **무엇을** 만들어야 하는가 (기능 ID·검수 기준·추적성) | `.claude/rules/rfp-harness.md` | `# Requirement:` 주석 검사, 요구 ID별 테스트 |
| 평가 하네스 | 만든 것이 **얼마나** 되는가 (Recall@5, 누락 건수, p95) | `ai/apps/evaluation/` | `cd ai && pytest`, 기준선 미달 시 CI 실패 |
| **구조 하네스 (이 문서)** | **어떻게 짜야** 위 둘이 계속 성립하는가 (계층·의존 방향·슬라이스) | `docs/harness.md` + `docs/architecture.md` | import-linter 계약 3+3종, 타입 체크 |

구조 규칙의 본문은 [architecture.md](architecture.md), 도메인 용어는 [domain.md](domain.md)에 있다. 이 문서는 **검증 장치**만 다룬다.

---

## 1. 코드 하네스 — import-linter 계약, 두 파일에 3종씩

2026-08-26 `fastapi/` 가 `server/`·`ai/` 로 갈리면서 **계약 파일도 둘이 됐다.**
각 기능 모듈은 스포크, `hub`는 7.3절 인터페이스 계약(전사·카드·종결)만 소유하는 허브다
(구조 근거 → [architecture.md §1](architecture.md)). 아래 계약이 세 직교 구조를 강제한다.

- **앱 내부** — 헥사고날/클린: `adapter → app → domain` (역방향 import 금지)
- **앱 사이** — 스타 토폴로지: 스포크끼리 직접 참조 금지, 허브는 스포크를 모른다
- **서브도메인 사이** — `ai → server` 한 방향만. `server → ai` 는 금지

### 1.1 파일 위치와 실행

```bash
cd server && PYTHONPATH=apps lint-imports --config .importlinter                # 3종
cd ai     && PYTHONPATH=apps:../server/apps lint-imports --config .importlinter # 3종
```

`ai` 쪽이 `../server/apps` 를 경로에 올리는 것은 **구조 문제가 아니라 경로 문제**다 —
`ai/` 모듈이 `hub` 포트(추상)를 구현하므로 그 정의를 찾을 수 있어야 한다.

`root_packages` 는 **실제로 존재하는 패키지만** 적는다 — 아직 없는 이름을 적으면
lint-imports 가 "모듈 없음"으로 실패한다. 지금은 `server`: `hub`·`core`, `ai`: `retrieval`·`evaluation`.
스포크를 새로 만들 때마다 해당 파일의 목록 전부에 이름을 추가한다(파일 안 주석이 절차를 안내한다).

스포크 이름은 `rfp-harness.md §3.1`의 코드 위치를 그대로 쓴다. 이름을 바꾸면 그쪽 표도 같이 바꾼다.

### 1.2 계약 요약

**`server/.importlinter`** — 요청이 흐르는 길

| 계약 | 종류 | 내용 |
|---|---|---|
| 클린 아키텍처 계층 | layers | 허브·전 스포크에서 `adapter > app > domain`. 계층이 없는 앱은 괄호로 허용 |
| **서브도메인 방향** | forbidden | `server` → `ai` import 금지. 함께 들어오는 `torch`·`transformers`·`langchain`·`langgraph` 도 금지 — 서버 컨테이너에 그것들이 있으면 방향이 이미 무너진 것이다 |
| 프레임워크 격리 | forbidden | `*.app`·`*.domain` → `fastapi`·`sqlalchemy`·`psycopg`·`elasticsearch` 등 금지 |

**`ai/.importlinter`** — 품질을 만들고 재는 쪽

| 계약 | 종류 | 내용 |
|---|---|---|
| 클린 아키텍처 계층 | layers | `adapter > app > domain` |
| 모듈 상호 독립 | independence | `ai` 모듈끼리 직접 import 금지. 접점은 `hub` 포트뿐 |
| **도메인 순수성** | forbidden | `domain`·`evaluation` → 프레임워크·**모델 라이브러리** import 금지 |

### 1.3 계약이 지키는 절대 원칙

| 계약 | 지키는 것 |
|---|---|
| 도메인 순수성 + 프레임워크 격리 | 절대 원칙 9 "판정은 규칙이, 설명만 LLM이" — 마스킹 판정·F-2 판정 코드가 `transformers`를 import 할 수 없다 |
| 도메인 순수성 (`evaluation` 포함) | 절대 원칙 1 "LLM을 채점자로 쓰지 않는다" — 채점 코드가 모델 라이브러리를 부를 수 없다. 규칙이 아니라 **구조**로 막는다 |
| 모듈 상호 독립 | `masking`이 `retrieval`을 몰라야 "자막·저장 양쪽 앞단" 위치가 유지된다 (C-5, SEC-1) |
| 분리 가능성 | `server` 가 `ai` 를 직접 import 하면 한 덩어리가 된다. ⚠ **지금은 한 컨테이너에 함께 배포한다**(`decisions/024`·`105` — `ai/` 는 서비스가 아니라 라이브러리다). 이 계약이 지키는 것은 «지금 갈라져 있다»가 아니라 **«나중에 가를 수 있다»** 이다 — 합성 루트(`main.py`)만 양쪽을 알기 때문에, `ai/` 를 서비스로 올릴 때 고칠 파일이 그 하나다 |
| 허브 격리 | 7.3절 계약이 특정 구현에 끌려가지 않는다 — 대시보드(조서희)·게이트웨이(정성윤)가 허브 DTO만 보고 병렬 작업 |

---

## 2. 검증 명령

**현재 실제로 도는 것만 적는다.** 없는 것은 "없음"이라고 쓴다.

| 영역 | 명령 | 상태 (2026-08-26) |
|---|---|---|
| 허브 계약·앱 기동 테스트 | `cd server && pytest` (`server/pytest.ini`: `integration` 마커는 기본 제외) | **동작** — 11개 통과 (테스트는 앱 안 `apps/hub/tests/`, 루트 `tests/`는 main.py 전용) |
| **평가 하네스**·검색 | `cd ai && pytest` | **동작** — 53개 통과 (`apps/evaluation/tests/`·`apps/retrieval/tests/`) |
| 구조 계약 (server) | `cd server && PYTHONPATH=apps lint-imports --config .importlinter` | **동작** — 계약 3종 통과 |
| 구조 계약 (ai) | `cd ai && PYTHONPATH=apps:../server/apps lint-imports --config .importlinter` | **동작** — 계약 3종 통과 |
| FastAPI 코어 실행 | `cd server && uvicorn main:app --reload --env-file ../.env` → `GET /health`·`GET /hub/myself`·`POST /hub/transcripts` | 동작 — 스포크 0개라 `/hub/transcripts`는 501 |
| Node 게이트웨이 | — | 없음 — 미스캐폴딩 (`services/` 디렉터리 자체가 아직 없다) |
| React 대시보드 타입 체크 | `cd apps/dashboard && pnpm run typecheck` | 스캐폴딩됨 — 다만 `node_modules` 미설치라 **로컬에서 아직 안 돌려봄**. CI 에도 이 job 은 없다 |
| 지킬 사이트 빌드 · 내부 링크 | `cd jekyll && bundle exec jekyll build` → `python3 scripts/check_site_links.py jekyll/_site` | **동작** — 56페이지, 깨진 링크 0 |

> 위 수치는 2026-08-26 실측이다. `cd server && pytest` 가 더 이상 평가 하네스를 돌리지 않는다는
> 점에 주의 — 분리 이후 평가 하네스는 `ai/` 에 있다. `rfp-harness.md §5` 의 모의 검수 항목도
> 같은 이유로 `cd ai && pytest` 를 함께 봐야 한다.
| ERD 재생성 | `python db/generate_schema_docs.py` | 동작 |

가짜 초록 경고 (redoceanmap에서 겪은 것):
- `npx tsc`는 로컬 `typescript`를 못 찾으면 레지스트리의 무관한 `tsc` 패키지를 설치하고 **exit 0**으로 끝난다. 대시보드가 생기면 반드시 `package.json` 스크립트(`pnpm run typecheck`)로 돌린다.
- `pytest`가 0개 수집되고 통과하는 것도 초록이다. 결과 줄의 **개수**를 확인한다.
- 평가 하네스의 "측정 불가 — 모듈 미구현"은 실패가 아니라 정직한 보고다. 이것을 통과로 바꾸는 유일한 방법은 모듈을 구현하는 것이다.

---

## 3. 문서 온톨로지

문서도 계층이 있다. 아래로 갈수록 상세하고, 위로 갈수록 짧다.

| 계층 | 위치 | 성격 | 길이 |
|---|---|---|---|
| 규칙 | `CLAUDE.md` (루트) | 모든 세션이 읽는 정본. 절대 원칙·기록 규칙·커밋 규칙 | **200줄 이내 유지** (넘으면 상세를 아래로 민다) |
| 경로 규칙 | `.claude/rules/*.md` | 특정 경로를 만질 때 자동 적용 (`paths:` 프론트매터) | 파일당 한 주제 |
| 상세 | `docs/*.md` (이 계층) | 구조·도메인·기획서 사본. 공개 저장소이지만 사이트에는 안 올라감 | 제한 없음 |
| 비공개 | `_project/` | 인수인계 상태, 결정 기록, 원본 기획서. 지킬 밖 | — |
| 공개 사이트 | `jekyll/` | 팀·외부가 보는 진행 기록과 문서화된 제안서 | — |

배치 규칙:
- 새 `.md`가 **규칙**이면 `CLAUDE.md`나 `.claude/rules/`, **설명**이면 `docs/`, **내부 사정**이면 `_project/`, **팀에 보이는 진행**이면 `jekyll/`.
- 같은 내용을 두 계층에 쓰지 않는다. 위 계층은 아래 계층으로 **링크**한다(일반 마크다운 상대 링크 — 이 저장소는 WikiLink를 쓰지 않는다).
- `docs/`도 공개된다. 약관 원문·자격증명·개별 사건 자료는 여기 두지 않는다 (`CLAUDE.md §8`).
- 영역 루트 `CLAUDE.md` 는 **2026-08-26 에 생겼다** — `server/CLAUDE.md`(요청이 흐르는 길)·`ai/CLAUDE.md`(품질을 만들고 재는 쪽).
  각 파일이 그 디렉터리가 하는 일/하지 않는 일, 의존 방향, 검증 명령을 규정한다. 충돌 시 루트 `CLAUDE.md` 가 우선한다.

---

## 문서 지도

| 문서 | 내용 |
|---|---|
| [CLAUDE.md](../CLAUDE.md) | 규칙 정본 |
| [architecture.md](architecture.md) | 헥사고날/클린 · 허브-스포크 · 수직 슬라이스 1:1 · SOLID 대응 |
| [domain.md](domain.md) | 도메인 모델 — 골든셋·지식베이스·DDL 기준 유비쿼터스 언어 |
| [plan-rev4.1.md](plan-rev4.1.md) | 기획서 rev.4.1 사본 (rev.4 + 보완지시서 병합) |
| [.claude/rules/rfp-harness.md](../.claude/rules/rfp-harness.md) | 요구사항 ID·검수 기준·추적성 |
| [ai/apps/evaluation/harness.py](../ai/apps/evaluation/harness.py) | 평가 하네스 골격 |
