# 아키텍처 — 헥사고날/클린 · 허브-스포크 · 수직 슬라이스 1:1

> `fastapi`(FastAPI 코어)의 구조 규칙. 강제 수단은 [harness.md](harness.md)의 import-linter 계약 5종,
> 용어는 [domain.md](domain.md). 기획서 아키텍처(구성요소)는 [plan-rev4.1.md §3](plan-rev4.1.md)이 정본이며
> 이 문서는 그 구성요소를 **코드로 어떻게 배치하는가**만 다룬다. 새 인프라·도구를 추가하지 않는다.

규칙의 근거는 헥사고날/클린 아키텍처 + DDD + SOLID다. 다만 원칙 이름을 외우는 것이 목적이 아니라,
**한 기능이 만들어야 할 파일 목록을 박아둬서 계층을 빼먹지 못하게 하는 것**이 목적이다(§3).

---

## 1. 스타 토폴로지 — 모듈 사이 구조 (허브-스포크)

`rfp-harness.md §3.1`의 코드 위치가 곧 스포크 목록이다. 여기에 `hub`를 더한다.
담당은 2026-08-26 **디렉터리 분리 기준**(`_project/decisions/012`)이다 — 스포크가 `ai/`에
있으면 류준, `server/`에 있으면 장민석. `decisions/005`의 "백엔드·AI 공동"은 이것으로 갱신됐다.

**도메인은 다산콜센터 하나다**(2026-08-28, `_project/decisions/201`). 스포크는 기능 축이고, 도메인 축은 사라졌다 —
`retrieval` 의 `domain` 필터는 값이 하나뿐이라 사실상 상수이고, B-0 도메인 라우팅 구현체는 삭제됐다.
~~도메인 4종은 스포크를 복제하지 않는다.~~ 스포크는 기능 축이고 도메인은 데이터 축이다 — `retrieval`이 `domain`으로 인덱스를 고르고, `closure_gate`가 도메인별 규칙표를 읽는다([domain.md §2](domain.md)).

| 패키지 | 위치 | 역할 | 기능 ID | 담당 |
|---|---|---|---|---|
| `hub` | `server/` | **허브** — 7.3절 인터페이스 계약 3종(전사 이벤트·추천 카드·종결 판정)을 DTO + 포트로 소유. 파이프라인 배선. 도메인 로직 없음 | 7.3절 | 장민석 (계약 변경은 류준과 합의, 4인 컨펌) |
| `masking` | `server/` | C-5 개인정보 마스킹 — 자막·저장 양쪽 **앞단** | C-5, SEC-1 | 정성윤 (P1~P5) / 류준 (P6~P7 NER, 여유 시) |
| `closure_gate` | `server/` | 종결 요건 검증 (조건부, 7주차 체크포인트) | F-2 | 장민석 |
| `postcall` | `server/` | 요약·유형 분류·공백 리포트 | D-1~D-4 | 장민석 (요약 모델 호출은 `ai/` 포트 경유) |
| `retrieval` | `ai/` | 트리거 판정 + 하이브리드 검색 + 리랭킹 | B-1~B-3 | 류준 |
| `generation` | `ai/` | 근거 기반 카드 요약 + 출처 + "관련 문서 없음", 폴백 모드 | B-4~B-6 | 류준 |
| `compliance` | `ai/` | 위반 탐지 + 대체 표현 | C-1~C-4 | 류준 |
| `evaluation` | `ai/` | 평가 하네스 (이미 존재 — `ai/apps/evaluation/`) | E-1~E-4 | 설계 류준 / 운영 정성윤 |

> **`generation`·`compliance` 의 위치를 `server/` → `ai/` 로 정정했다 (2026-08-26).**
> `rfp-harness.md §3.1`은 분리 이전 표기라 둘을 `server/apps/` 로 적어 뒀지만, 두 모듈 다
> 모델(EXAONE·분류기)을 로드한다. **`server/.importlinter` 계약 2가 `server/` 안에서
> `torch`·`transformers`·`langchain`·`langgraph` import 를 금지**하므로 거기서는 애초에
> 만들 수 없다. 문서가 아니라 계약이 이미 정답을 갖고 있던 경우다.
> ⚠ 장민석 확인 대상 — `jekyll/open-items.markdown` 참고.

| 방향 | 허용 | 이유 |
|---|---|---|
| 스포크 → 허브 | ✅ | 스포크는 허브 DTO·포트에만 의존 |
| 스포크 → 스포크 | ⛔ | 직접 import·순환 금지. 교차 협력은 허브 경유 |
| 허브 → 스포크 | ⛔ | 허브가 특정 스포크를 알면 스타가 메시로 무너진다 |

**파이프라인은 허브가 배선한다.** 전사 이벤트 하나가 흐르는 순서는 기획서 §3 다이어그램 그대로다:

```
게이트웨이(Node) ──WebSocket──▶ hub
                                 │ TranscriptEvent (원문)
                                 ▼
                          masking  ──▶ TranscriptEvent (마스킹됨)   ← 이 지점 뒤로만 저장·표시 허용
                                 │
                 ┌───────────────┼───────────────┐
                 ▼               ▼               ▼
            retrieval       compliance      closure_gate (요청 시)
                 │ 문서 ID·점수     │ 위반·대체 표현     │ verdict·missing
                 ▼               │               │
            generation           │               │
                 │ RecommendationCard             │ ClosureVerdict
                 └───────────────┴───────────────┘
                                 ▼
                       hub ──▶ 게이트웨이 ──▶ 대시보드(React)
```

**현재 상태(2026-08-26)**: `hub`는 슬라이스 2개(`transcript_ingest` — `POST /hub/transcripts`, `myself` — `GET /hub/myself`)가 §3 단면대로 존재하고, 계약 DTO 3종 + 스포크 포트 6개(마스킹·트리거·검색·생성·컴플라이언스·게이트)를 소유. `core/config.py`·`main.py`(합성 루트, `/health`)·`evaluation/`. **스포크 0개** — `POST /hub/transcripts`는 masking 스포크가 꽂히기 전까지 501을 돌려준다(마스킹 없이 원문을 흘리는 임시 통과는 만들지 않는다, SEC-1).

허브가 각 스포크를 호출하는 방식은 **허브가 정의한 아웃바운드 포트**를 스포크가 구현하는 것이다.
스포크는 허브 포트를 import 하고, 허브는 DI(`dependencies/`)로 구현체를 받는다. 허브 코드에 `import masking`이 나오면 계약 위반이다.

`evaluation`은 예외적으로 파이프라인 밖에 있다. 골든셋을 읽어 각 스포크를 **직접** 채점하되, 접점은 **허브 아웃바운드 포트 그 자체**다 — `apps/evaluation/harness.py`의 `Ports(retrieval=…, masking=…)`에 스포크가 구현한 `apps/hub/app/ports/output/*` 객체를 꽂는다. 스포크 하나에 계약이 둘(허브 포트 + 평가용 Protocol)이면 반드시 갈라지므로 평가 전용 Protocol은 두지 않는다(2026-08-26 이중화 해소). 포트 시그니처를 바꾸면 `evaluation`도 같이 고친다.

---

## 2. 앱 내부 레이어 (헥사고날)

허브·스포크 모두 같은 단면이다. 앱은 전부 `server/apps/<앱>/` 아래에 있고, `apps/`가 PYTHONPATH에 올라가므로 import는 `hub.app…`처럼 **앱 이름부터** 쓴다(`apps.`를 붙이지 않는다 — 레퍼런스 `minseok/apps/`와 동일).

```
apps/<spoke>/
├── domain/
│   ├── entities/            # 식별자 있는 것 (Call, TranscriptSegment, Closure …)
│   ├── value_objects/       # 값으로 비교되는 것 (PiiSpan, DocRef, Verdict …)
│   └── services/            # 순수 규칙 계산 (마스킹 규칙, F-2 판정, RRF 병합 …)
├── app/
│   ├── ports/input/         # UseCase ABC — 밖에서 이 스포크를 부르는 계약
│   ├── ports/output/        # Repository/Gateway ABC — 이 스포크가 밖에 요구하는 계약
│   ├── use_cases/           # Interactor — 포트를 엮는 대장
│   └── dtos/                # 계층 간 전달 객체 (frozen dataclass; pydantic 허용)
├── adapter/
│   ├── inbound/api/schemas/ # pydantic 요청/응답 스키마 (HTTP 표면이 있는 앱만)
│   ├── inbound/api/v1/      # FastAPI 라우터 — 스키마 ↔ DTO 변환은 여기서만
│   └── outbound/            # log_*_adapter.py · es/ postgres/ hf/ stt/ — 외부 시스템 구현체
├── dependencies/            # FastAPI DI 프로바이더 (포트 ↔ 구현체 결합은 여기서만)
└── tests/
    ├── app/use_cases/       # 인터랙터 — 스텁 포트로
    └── adapter/             # 라우터·어댑터 — TestClient, 실인프라는 integration 마커
```

**의존 방향: `adapter → app → domain`.** 역방향 금지.

| 계층 | 알아도 되는 것 | 몰라야 하는 것 |
|---|---|---|
| `domain` | 표준 라이브러리, 같은 스포크의 domain | pydantic, fastapi, ES 클라이언트, 모델 라이브러리, 다른 스포크 |
| `app` | domain, 허브 DTO·포트, pydantic(dtos 한정) | fastapi, sqlalchemy, elasticsearch, transformers, torch |
| `adapter` | 전부 | 다른 스포크의 adapter |

이 표가 곧 [harness.md](harness.md) 계약 3·4다. 절대 원칙 9("판정은 규칙이, 설명만 LLM이")는 이렇게 코드가 된다:
**마스킹 판정과 F-2 판정은 `domain/services/`에 산다. 거기서는 모델을 import 할 수 없다.** LLM 호출은 `generation`의
`adapter/outbound/hf/`에만 있고, 그 결과는 카드의 `summary` 문자열일 뿐 어떤 판정에도 쓰이지 않는다.

---

## 3. 수직 슬라이스 1:1 컨벤션 (필수)

**슬라이스 = 기능 ID 하나**(`rfp-harness.md §1-2` 원자성 규칙과 같은 말이다). 새 슬라이스를 만들 때
아래 파일이 **계층마다 1개씩** 존재해야 한다. 이름 `<이름>`이 전 계층을 관통한다 — "프랙탈 단면".

```
adapter/inbound/api/schemas/<이름>_schema.py     # 요청/응답 pydantic 스키마 (HTTP 표면이 있을 때만)
adapter/inbound/api/v1/<이름>_router.py          # 라우터 (위와 짝)
app/dtos/<이름>_dto.py                           # Query/Command · Result (frozen dataclass)
app/ports/input/<이름>_use_case.py               # UseCase ABC
app/ports/output/<이름>_record_port.py           # 활동 기록 아웃바운드 포트 (인터랙터가 실제 사용)
app/use_cases/<이름>_interactor.py               # 대장 — 포트를 실제로 호출
adapter/outbound/log_<이름>_record_adapter.py    # 임시 로그 구현 (영속 필요 시 postgres/ 로 교체)
dependencies/<이름>_provider.py                  # DI
tests/app/use_cases/test_<이름>_interactor.py    # 스텁 포트로 검증

실례: `apps/hub/`의 `transcript_ingest`·`myself` 슬라이스가 이 단면 그대로다.
```

규칙:
1. **기계적 파일명 일치가 아니라 "계층마다 담당 파일 1개"가 기준이다.** 허용 예외 3종:
   - ① HTTP 표면 없는 슬라이스는 `router`/`schema`를 만들지 않는다 (빈 스켈레톤 금지). `masking`·`retrieval`의 트리거처럼 허브가 포트로만 부르는 파이프라인 내부 모듈이 대부분 여기 해당한다.
   - ② DTO·리포지토리는 도메인어로 명명해도 된다 (`transcript_dto`, `document_repository` 등).
   - ③ `entity`/`value_object`/`mapper`는 **로직이 있을 때만** 만든다. 필드만 있는 클래스를 위해 파일을 만들지 않는다.
2. **한 파일에 여러 슬라이스를 담지 않는다.** 라우터·스키마·프로바이더·테스트 잡탕 금지. `retrieval_router.py`에 B-1과 B-2 엔드포인트가 같이 있으면 쪼갠다.
3. **유스케이스는 어댑터 스키마가 아니라 `app/dtos`를 받는다.** 스키마 ↔ DTO 변환은 라우터 몫이다.
4. **아웃바운드 포트는 빈 껍데기 금지.** 인터랙터가 실제로 호출하는 메서드만 정의한다.
5. **모든 파일 상단에 `# Requirement: <ID>`.** (`rfp-harness.md §1-3`)
6. 검증 루틴: 라우트 표 전후 diff + `cd server && pytest` + `PYTHONPATH=apps lint-imports`([harness.md §2](harness.md)).

### 3.1 자기소개 엔드포인트 `GET <prefix>/myself` (HTTP 표면이 있는 스포크만)

HTTP 표면이 있는 스포크는 `GET <prefix>/myself` 를 함께 만든다. **실제 기능**을 설명한다 — 제공 엔드포인트·데이터·제약.
자기소개도 §3의 단면을 관통한다(별도 슬라이스, 라우터 분리). 두 가지 제약이 이 프로젝트에 추가된다:

- 부록 A-1 발언 범위를 지킨다. "안전합니다", "위험도 N%", "완벽히 차단" 류 문구는 자기소개에도 쓰지 않는다. "정의된 P1~P5 패턴에 대해 누락 0건을 목표로 한다"처럼 범위를 붙여 쓴다.
- **하지 않는 것**을 명시한다 (예: "종결 가능 여부를 생성 모델로 판정하지 않습니다").

---

## 4. SOLID 대응표

원칙이 이 구조의 어느 장치로 담보되는지. 장치가 없는 원칙은 지켜지지 않는 것으로 본다.

| 원칙 | 담보 장치 | 이미 있는 사례 |
|---|---|---|
| **S**RP | 슬라이스 1:1 — 파일 하나 = 기능 ID 하나 = 바뀌는 이유 하나 | `apps/evaluation/metrics/{retrieval,trigger,compliance,masking,closure_gate,latency}.py` |
| **O**CP | 스포크 추가 = 허브 포트 구현체 추가. 허브·다른 스포크 수정 없음 | `main.py`의 `dependency_overrides` + `evaluation.harness.Ports(...)` — 구현체를 꽂기만 |
| **L**SP | 포트 ABC의 시그니처를 구현체가 그대로 만족. `def`/`async def` 일치 | `apps/hub/app/ports/output/*` ABC 6종 |
| **I**SP | 아웃바운드 포트는 인터랙터가 실제로 부르는 메서드만 (§3 규칙 4) | `MaskingPort.mask` 하나뿐 — 호출자는 `transcript_ingest_interactor`·`evaluation.harness` |
| **D**IP | `app/ports`(추상)를 `adapter`(구체)가 구현. import-linter 계약 1·3이 역방향을 실패시킴 | `evaluation`이 스포크를 모른 채 허브 포트로만 채점 |

DDD 쪽 대응: 바운디드 컨텍스트 = 스포크, 유비쿼터스 언어 = [domain.md](domain.md), 애그리거트·VO는 `domain/`에서만, 리포지토리는 `app/ports/output`의 ABC.

---

## 5. 코딩 컨벤션 (fastapi)

- **주석·문서·커밋 메시지는 한국어.** 커밋은 `CLAUDE.md §7` 형식.
- I/O-bound(DB·ES·모델 추론·STT)는 `async def`, CPU-bound(정규식·RRF·판정)는 `def`. 포트(ABC)와 구현체의 `def`/`async def`를 일치시킨다. 무거운 CPU 작업은 호출 측에서 `asyncio.to_thread`.
- 환경변수는 `.env.example`에 **키 이름만** 등록하고(`SEC-2`), `os.environ`을 읽는 곳은 `core/config.py` 하나뿐이다. 스포크에서 `os.getenv`·`load_dotenv`를 새로 쓰지 않는다.
- 마스킹 전 원문은 `hub`의 `TranscriptIngestCommand` → `transcript_ingest_interactor`가 `MaskingPort.mask()`를 부르기 전까지만 존재한다. 기록 포트·로그·DB·다른 스포크로 나가는 모든 문자열은 마스킹 후 `TranscriptEvent`다 (`SEC-1`). 원문을 받는 포트 시그니처를 만들지 않는다.
- 목표 수치를 코드에 하드코딩하지 않는다. 임계값은 `apps/evaluation/metrics/*.py`의 상수(`ON_TIME_WINDOW_MS` 등)가 정본이고, 기획서 6.1절과 함께 바꾼다.
- 테스트: 유스케이스는 **스텁 포트**로(mock 프레임워크보다 스텁 구현 선호), 실제 ES·PostgreSQL·STT가 필요한 것은 `@pytest.mark.integration`.

---

## 6. 아직 정하지 않은 것

- **도메인 라우팅** — 통화가 4개 도메인 중 어디인지 누가·언제 판정하는가(게이트웨이 메타데이터? `retrieval` 첫 발화 분류?). 7.3절 계약에 `domain` 필드가 없다 → v3 필요. 라우팅 정확도는 지표로 편입해야 한다.

- 각 스포크 `adapter/outbound/` 하위 이름(`es`/`postgres`/`hf`/`stt`)은 제안이다. [Task 1] 때 확정하고 이 문서를 고친다.
- Node 게이트웨이(`services/gateway`)·React 대시보드(`apps/dashboard`)의 계층 규칙은 이 문서 범위 밖이다. TypeScript라 import-linter를 못 쓰므로 스캐폴딩 시 `dependency-cruiser` 또는 `eslint-plugin-boundaries` 중 하나를 고른다 — 미결.
- 허브가 F-2 게이트를 "요청 시"에만 부르는지, 종결 시도 이벤트를 게이트웨이가 별도 메시지로 보내는지는 7.3절 계약 v2에 없다. 7주차 체크포인트 전에 정한다.
