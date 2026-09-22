# 213 — `ai/` 의 모델을 HTTP 로 연다 — 표면은 `ai/` 안, FastAPI, 서비스 토큰, 안 실렸으면 503

- 날짜: 2026-09-22
- 작성: 류준 (`2xx` 번호대)
- 상태: 채택 — **`ai/` 쪽 표면만 구현됐다.** 서버 원격 어댑터(`w6-server-remote-model-adapter`, 장민석)와 GPU 인스턴스(`121`)는 없다.
  운영은 이 결정으로 **아무것도 바뀌지 않는다** — 규칙 마스킹 + BM25 + 스니펫 카드 그대로다
- 관련: [121](121-모델은-전용-GPU-EC2-에-올린다-서버-파드에는-싣지-않는다.md)(모델은 전용 GPU EC2 — 이 결정이 답하는 질문의 출처) ·
  [024](024-검색-스포크를-같은-프로세스에서-꽂는다.md)·[105](105-배포는-한-컨테이너-도메인도-하나.md)(`ai/` 는 라이브러리 — **이 결정이 그 전제를 깬다**) ·
  [120](120-쓰기-경로는-서비스-토큰으로-잠근다-상담원-토큰과-가른다.md)·[110](110-테스트-음성-파일을-S3-에-보관한다-발급은-server-문은-토큰.md)(서비스 토큰 · fail-closed) ·
  [206](206-검색-구성-임베딩-리랭킹-RRF-비채택.md)·[207](207-B4-생성-모델을-kanana-로-바꾼다.md)·[208](208-운영에-NER과-임베딩을-켜는-순서.md)
- 티켓: [w6-ai-model-http-surface](/backlog/w6-ai-model-http-surface/) — 다음: [w6-server-remote-model-adapter](/backlog/w6-server-remote-model-adapter/)

---

## 맥락

`121` 이 모델(NER · 임베딩 · 리랭커 · 생성)을 서버 파드(`t3.large`)가 아니라 **전용 GPU EC2** 에 올리기로 했다.
모델이 다른 머신에 있으면 서버가 그것을 부를 **문**이 필요하다. 지금 `ai/` 에는 그 문이 없다 —
`024`·`105` 가 `ai/` 를 **서버와 같은 프로세스에 실리는 라이브러리**로 정했고, `ai/requirements.txt` 에 웹 프레임워크가
없다는 것이 그 결정들의 근거 ①이었다. 이 결정이 **그 전제를 깬다.** 그래서 결정 기록으로 남긴다.

`121` 은 이 전환이 여는 질문 다섯을 적어 두었다(아래 「121 의 질문 — 무엇에 답했나」). 이 기록은 **그중 일부에만** 답한다.

## 선택지

### 표면을 어디에 두나

| 후보 | 판단 |
|---|---|
| **`ai/apps/model_serving/` (inbound 어댑터) + 합성 루트 `ai/model_server.py`** | 모델 어댑터(`pii_ner`·`retrieval`·`generation`)가 이미 `ai/` 에 있다. 표면 모듈은 그것들을 import 하지 않고(계약 2) Protocol 로만 받고, 꽂는 것은 `apps/` 밖 합성 루트가 한다 — `provider.py` 가 `server/main.py` 를 위해 하는 일과 같은 자리 |
| 새 최상위 디렉터리(`model-service/`) | 모델 어댑터를 복사하거나 `ai/` 를 경로로 끌어와야 한다. 복사하면 **구간 규칙이 두 벌**이 되어 운영과 측정이 다른 것을 재게 된다 |
| `server/` 안에 | `server/.importlinter` 계약 2 가 torch·transformers 를 금지한다. 서버 이미지를 가볍게 두려는 `121` 의 목적 자체와 반대다 |

### 프레임워크

| 후보 | 판단 |
|---|---|
| **FastAPI + uvicorn** | 서버가 이미 쓴다(`server/requirements.txt` 0.141.1 · 0.52.4) — **같은 버전을 고정**해 루트 `.venv` 하나로 둘이 돈다. pydantic 검증·TestClient 를 그대로 쓴다. 새로 배울 것이 없다 |
| 표준 라이브러리 `http.server` | 의존성은 0 이지만 검증·동시성·테스트 도구를 손으로 만든다. 요청 모양이 넷이라 그 비용이 이득보다 크다 |
| gRPC | 스트리밍·이진 벡터에 유리하지만 서버 쪽 어댑터가 새 도구를 들여야 한다. 지금 병목이 직렬화라는 측정이 없다 |

### 인증

| 후보 | 판단 |
|---|---|
| **서비스 토큰 하나(`MODEL_SERVICE_TOKEN`) · `Authorization: Bearer` · 없으면 닫힌다** | 부르는 쪽이 사람이 아니라 서버다(`120` 과 같은 구조). 바이트 `compare_digest`. **처음부터 fail-closed** — `120` 의 「없으면 연다」는 이미 돌고 있는 미디에이터를 401 로 만들지 않으려는 이행기 동작이었고, 이 표면은 **부르는 쪽이 아직 없어서** 이행기가 필요 없다. `110`(업로드 문)과 같은 모양이다 |
| 보안 그룹만 믿는다 | 인스턴스가 아직 없어 보안 그룹도 없다. 망 설정 하나가 틀리면 발화가 그대로 흘러 들어오는 문이 된다 |

## 결정

**`ai/apps/model_serving/`(표면) + `ai/model_server.py`(합성 루트), FastAPI, 서비스 토큰(fail-closed).**

```
cd ai && uvicorn --factory model_server:create_app --host 0.0.0.0 --port 8100 --no-access-log
```

### 엔드포인트

| 메서드·경로 | 요구 ID | 요청 | 200 응답 |
|---|---|---|---|
| `GET /health` | — | (인증 없음) | `{"status":"ok","auth":"locked"\|"unconfigured","models":{"ner"\|"embedding"\|"rerank"\|"generation":{"loaded":true,"model":…}\|{"loaded":false,"reason":…}}}` |
| `POST /v1/ner/spans` | C-5 | `{"text"}` (≤2,000자) | `{"model","spans":[{"pattern":"P6"\|"P7","start","end"}],"elapsed_ms"}` |
| `POST /v1/embeddings` | B-2 | `{"kind":"query"\|"passage","texts":[…]}` (1~64건) | `{"model","dims","vectors","truncated","elapsed_ms"}` |
| `POST /v1/rerank` | B-3 | `{"query","passages":[…]}` (1~50건) | `{"model","scores","elapsed_ms"}` — **입력 순서 그대로** |
| `POST /v1/generation/cards` | B-4~B-6 | `{"utterance","docs":[{"doc_id","title","snippet","score"}]}` (≤10건) | `{"model","cards":[Card],"outcomes":[{"doc_id","outcome"}],"elapsed_ms"}` |

- **NER 은 구간만 준다 — 마스킹 판정이 아니다**(절대 원칙 9). 가린 텍스트도 「가려야 한다」는 결론도 돌려주지 않는다.
  구간은 모델 태그를 **`pii_ner` 의 규칙**(`detect_entities_with_rejoin` — 어절 확장·조사 벗기기·1음절 재결합)이 다듬은 것이고,
  같은 함수를 `LayeredMaskingAdapter`(같은 프로세스 구성)도 쓴다. **P1~P7 규칙과 합집합을 만들어 실제로 가리는 일은 서버**다.
- `elapsed_ms` 는 **표면 안의 추론 시간**이다. 부르는 쪽이 잰 벽시계에서 이것을 빼면 **네트워크 홉 + 직렬화 몫**이 나온다 —
  아래 질문 2 를 잴 때 쓰라고 넣었다.
- `outcomes` — 생성 어댑터는 실패하면 스니펫 카드로 내려간다(`207`). 그 사실이 밖에서 보이게 조항별 결과를 싣는다. **원출력은 싣지 않는다.**

### 오류 계약 — 조용한 빈 결과를 내지 않는다

본문은 전부 `{"code", "model"?, "reason"?}` 한 모양이다. **부르는 쪽이 상태 코드만 보고 규칙·BM25·스니펫으로 내려갈 수 있어야 한다**(`121` 4번).

| 상태 | `code` | 뜻 |
|---|---|---|
| 401 | `unauthorized` | Bearer 가 없거나 틀렸다(`WWW-Authenticate: Bearer`) |
| 503 | `auth_not_configured` | 표면에 `MODEL_SERVICE_TOKEN` 이 없다 — **fail-closed**. 헤더가 무엇이든 추론하지 않는다 |
| 503 | `model_not_loaded` | 그 모델이 안 실렸다. `reason`: `not_configured` · `load_failed:<예외 유형>` |
| 503 | `model_unavailable` | 생성을 시도한 조항이 **전부** Ollama 오류 — 스니펫 카드로 채운 200 을 주지 않는다 |
| 500 | `inference_failed` | 추론 중 예외. `reason` 은 예외 **유형**만 |
| 422 | `invalid_request` | 모양·길이 위반. `fields` 는 필드 위치만 — **입력값을 되돌려주지 않는다** |

**「모델이 실렸고 아무것도 못 찾았다」(200 · `spans: []`)와 「모델이 없다」(503)는 다른 응답이다.** 앞의 것만 정상 빈 결과다.
생성에서 `docs: []` → `cards: []` 는 「관련 문서 없음」(B-6)이고 정상이다.

### SEC-1 · SEC-2

- 요청 본문을 찍는 미들웨어를 두지 않는다. 실패 로그는 예외 유형만. `--no-access-log` 로 띄운다(uvicorn 접근 로그도 본문은 찍지 않지만 경로·시각이 남을 이유가 없다).
- **FastAPI 기본 422 는 `input` 에 요청 값을 그대로 되돌려준다** — 발화가 부르는 쪽의 오류 로그로 샌다. 핸들러를 바꿨다(테스트로 고정).
- `/health` 는 **상태만** — 토큰 값·모델 경로를 싣지 않는다. `/docs`·`/openapi.json` 은 끈다.

### 설정 — 서버와 같은 이름

`PII_NER_MODEL_DIR` · `RETRIEVAL_EMBED_MODEL_DIR` · `RETRIEVAL_RERANK_MODEL_DIR` · `OLLAMA_URL` + `GENERATION_MODEL`(둘 다 있어야) —
`server/core/config.py` 와 **같은 변수명**이다. 추가는 `MODEL_SERVICE_TOKEN` · `MODEL_DEVICE`(`cpu` 기본, 자동 선택 안 함) · `GENERATION_TOP_N`(기본 1).
**모델 하나가 못 떠도 프로세스는 뜬다** — 그 자리만 503.

### 의존 방향 — `ai → server` 그대로

- `model_serving` 은 hub DTO(`Card`·`RetrievedDoc`)만 import 한다 — 방향은 `ai → server`.
- **`server/` 는 `model_serving`·`model_server` 를 import 하지 않는다 — HTTP 로만 닿는다.**
  `ai/tests/test_dependency_direction.py` 가 `server/**/*.py` 전체를 AST 로 검사한다(fastapi 없이 돌아 CI `ai` job 에서 실제로 돈다).
  ⚠ `ai/.importlinter` 로는 못 건다 — `hub` 등을 `root_packages` 에 올리면 `evaluation → hub.dtos → pydantic` 같은 간접 경로가
  계약 3 에 새로 잡혀 **기존 계약의 뜻이 바뀐다.** `server/.importlinter` 계약 2 의 금지 목록에 `model_serving` 을 넣는 것이
  제자리다 — **이 작업 범위(`ai/` 만) 밖이라 넣지 않았다.** (같은 목록에 `compliance`·`generation`·`pii_ner`·`postcall_summary` 도 빠져 있다.)
- `ai/.importlinter` 에는 등록했다 — `root_packages` · 계약 1(계층) · 계약 2(모듈 독립) · 계약 3(`model_serving.app` 은 fastapi·torch 를 모른다). **3계약 KEPT.**

## 근거

1. **포트는 그대로, 어댑터만 바뀐다.** `121` 이 짚은 대로 `RetrievalPort`·`MaskingPort`·`GenerationPort` 는 한 글자도 안 바뀐다.
   서버 쪽은 이 표면을 부르는 **outbound 어댑터**를 달면 되고(`024` 「되돌리는 법」 2번이 이미 그 모양을 적어 두었다), 그건 `server/` 안이라 계약 위반이 아니다.
2. **구간 규칙이 한 벌이다.** NER 구간을 만드는 규칙을 `pii_ner` 한 함수로 모았다. 같은 프로세스 구성과 원격 구성이 같은 규칙을 쓴다 —
   하네스로 잰 C-5 수치가 원격 구성에도 **규칙 부분만큼은** 그대로 옮겨 간다(모델 부분은 같은 가중치일 때에만).
3. **`024` 의 전제는 목적이 아니라 수단이었다.** `024`·`105` 가 막으려던 것은 「없는 서비스를 새로 만드는 일」과 「홉이 예산을 먹는 일」이다.
   `121` 이 모델을 다른 머신으로 보내기로 한 순간 서비스는 **필요해졌고**, 홉은 **피할 수 없게** 됐다. 남은 일은 그 홉을 재는 것이다(질문 2).

## `121` 의 질문 — 무엇에 답했나

**숨기지 않고 적는다.** 다섯 중 **1 은 답했고, 4 는 표면 쪽 절반만 답했고, 2·3·5 는 열려 있다.**

| # | `121` 의 질문 (원문 요지) | 이 기록 |
|---|---|---|
| 1 | **`ai/` 가 「라이브러리」에서 「서비스」가 된다.** HTTP(또는 gRPC) 표면이 필요하고, `ai/requirements.txt` 에 웹 프레임워크가 없다는 `024` 의 전제가 깨진다 | **답했다.** 위치 `ai/apps/model_serving/` + `ai/model_server.py` · FastAPI/uvicorn(서버와 같은 버전 고정) · 서비스 토큰 fail-closed · 엔드포인트 넷 · 오류 계약. `ai/requirements.txt` 에 fastapi·uvicorn·httpx 를 넣었다. ⚠ `ai/` 는 **라이브러리이기도 하다** — 같은 프로세스 구성(`provider.py` → `server/main.py`)은 그대로 살아 있다 |
| 2 | **런북 부록 A-1(「서버와 GPU 를 분리하지 않는다」)과 반대다.** 분리하면 검색·마스킹마다 홉이 붙는다 — **4.3절 예산(내부 처리 p95 ≤ 1,000ms)에 그 몫을 더해 다시 재야 한다.** 특히 C-5 는 자막·저장의 앞단이라 모든 발화가 그 왕복을 기다린다 | **열려 있다 — 미측정.** 홉 지연은 **한 번도 재지 않았다**(GPU 인스턴스도, 서버 원격 어댑터도 없다). 「괜찮다」고 쓰지 않는다(절대 원칙 2). 이 기록이 한 것은 **잴 수 있게 만든 것**뿐이다 — 응답의 `elapsed_ms`(표면 내부)와 부르는 쪽 벽시계의 차가 홉 몫이다. 아래 「로컬 참고」는 **홉이 없는** 표면 내부 시간이라 이 질문의 답이 아니다 |
| 3 | **비용과 자동 중지.** `g4dn.xlarge` 24/7 ≈ $597(예산 초과). `116` ①(자동 중지 안 함)은 `t3.large` 전제라 GPU 인스턴스에는 옮겨 가지 않는다 | **열려 있다.** 인프라 소관(정성윤). 표면은 **자주 꺼지는 것을 전제로** 설계했다는 것만 말할 수 있다 — 연결 거부·503 이 곧바로 드러나고, 콜드 스타트 적재 시간(로컬 CPU 3.3s)은 기동 때 한 번이다 |
| 4 | **GPU 가 꺼져 있을 때의 동작.** 원격이 안 붙어도 규칙·BM25 로 내려가야 하고, GPU 가 꺼졌다고 자막·마스킹이 멈추면 안 된다 | **표면 쪽 절반만 답했다.** 표면은 **조용한 빈 결과를 내지 않는다** — 꺼짐(연결 거부) · 미적재(503 `model_not_loaded`) · 백엔드 오류(503 `model_unavailable`) · 추론 예외(500)가 서로 다른 신호로 나간다(테스트로 고정). **실제로 내려가는 쪽(타임아웃·폴백·폴백 표시)은 서버 원격 어댑터**(`w6-server-remote-model-adapter`, 장민석) 몫이고 **아직 없다** |
| 5 | **6주차 판정(09-30)의 기준선 구성.** GPU 인스턴스가 떠서 운영 경로에 붙어 있으면 모델 구성, 아니면 운영 구성(규칙 + BM25)을 기준선으로. **떠 있지 않은 구성의 수치로 「통과」를 선언하지 않는다** | **열려 있다 — 이 기록으로 바뀌는 것이 없다.** 2026-09-22 현재 인스턴스도 서버 어댑터도 없으므로 `121` 5번의 규칙대로라면 기준선은 **운영 구성**이 된다. 표면이 생겼다는 사실이 모델 구성을 「운영 경로에 붙었다」로 만들지 않는다 |

## 로컬 참고 (측정값이 아니다)

`2026-09-22 10:55` · Apple M 계열 **CPU** · `CALLGUARD_MODELS_DIR=…/models pytest -m slow -s tests/test_model_server.py` ·
`TestClient`(같은 프로세스 — **네트워크 홉 없음**) · 요청 5회 중앙값, 응답 `elapsed_ms`:

```
적재 3.3s · ner 11.39ms · embed(1건) 39.27ms · rerank(후보 6) 85.02ms
```

**4.3절 예산에 대한 판단 근거로 쓰지 않는다.** 표본 5 · CPU · 홉 없음 · 하네스(`ai/apps/evaluation/`)가 낸 값이 아니다(§5).
생성은 Ollama 가 없어 재지 않았다.

## 남는 것

- **CI `ai` job 이 fastapi·httpx·uvicorn 을 설치하지 않는다**(`test.yml` 은 `pytest pydantic import-linter numpy` 만). 그래서 표면 테스트는
  **CI 에서 건너뛴다**(`importorskip`) — 로컬에서만 돈다. `test.yml` 의 `ai` job 설치 줄에 `fastapi==0.141.1 httpx==0.28.1 uvicorn==0.52.4` 를
  더하면 CI 에서도 돈다. `.github/` 는 이 작업 범위 밖이라 고치지 않았다. **의존 방향 검사는 fastapi 없이 돌아 CI 에서도 돈다.**
- `server/.importlinter` 계약 2 의 금지 목록에 `model_serving` 추가(위 「의존 방향」) — `server/` 소관.
- 배포 산출물(이미지·k8s·보안 그룹) 없음 — 인스턴스가 생길 때(`121`). 표면 자체는 **CPU 로도 돈다**(로컬 참고).
- 생성 표면의 `/health` `loaded` 는 「설정됐다」까지만 말한다 — Ollama 를 기동 때 ping 하지 않는다(`024` 와 같은 이유: 백엔드가 잠깐 없다고 표면이 못 뜨면 안 된다).
  Ollama 가 죽어 있으면 **요청에서** 503 `model_unavailable` 로 드러난다.

## 되돌리는 법

1. `ai/apps/model_serving/` · `ai/model_server.py` · `ai/tests/test_model_server.py` · `ai/tests/test_dependency_direction.py` 를 지우고
   `ai/.importlinter` 의 `model_serving` 줄(5곳)과 `ai/requirements.txt` 의 「모델 HTTP 표면」 3줄을 뺀다. 같은 프로세스 구성은 이 결정과 무관하게 돈다.
2. `pii_ner` 의 `detect_entities_with_rejoin`·`NerSpanDetector` 는 남겨도 된다 — `LayeredMaskingAdapter` 가 앞의 것을 쓴다(동작은 이 결정 전과 같다).
3. `121` 을 철회해 모델을 서버 파드로 되돌리면(`208`) 이 표면은 쓸 곳이 없어진다 — 1번을 한다.
