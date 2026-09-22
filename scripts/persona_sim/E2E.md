# 합성 통화 E2E 왕복 검사 — `e2e_check.py`

> 대본 → 재생기 → 콜 미디에이터 `/dev/text` → 서버(`POST /hub/calls`·`/hub/transcripts` → 마스킹·트리거·검색·콜 가드·필요서류)
> → **PostgreSQL** → `/ws` → 그리고 **대시보드 「상담기록 재생」이 읽는 `GET /hub/calls/{id}/transcript`·`/record`** 까지
> 갔다 돌아왔는지를 **규칙으로** 판정한다. 대시보드(`apps/call`)는 고치지 않는다 — 대시보드가 부르는 API 를 대신 부른다.
>
> ⚠ **`source: synthetic`.** 대본을 글자로 흘리므로 STT 를 거치지 않는다 — 여기서 나온 탐지·마스킹 결과는 **상한**이고,
> 성능 수치로 인용하지 않는다(절대 원칙 2·10). 이 검사가 말하는 것은 «배선이 끝까지 이어져 있는가» 뿐이다.

## 1. 로컬 스택 (이 맥에서)

```bash
# ① Elasticsearch — 이미 떠 있으면 건너뛴다 (`callguard-elasticsearch`, 9200). 101청크(99조항, 여권 4.23 포함 — 2026-09-22)가 있는지:
curl -s localhost:9200/_cat/indices            # callguard-kb-single … 101
#    없으면: docker build -t callguard-es:local infra/elasticsearch/ && (infra/README.md 「로컬 개발」 명령) && \
#            .venv/bin/python scripts/index_knowledge_base.py --to-es --recreate --embed-model models/koe5   # --embed-model 을 빼면 dense 가 0건

# ⚠ 2026-09-22: 이 맥은 5432 를 다른 프로젝트가 써서 `callguard-postgres` 를 127.0.0.1:**5434** 로 띄웠다 — 아래 5432 를 그 포트로 바꿔 쓴다.
#    8000·8080 도 다른 컨테이너가 쓰면 서버 :8001 · 콜 미디에이터 :8081 로(`--core-url`·`--mediator-url`).
# ② PostgreSQL — infra/README.md 의 개발용 컨테이너. 이름 볼륨 `callguard-pg` 는 옛 스키마(22 테이블)일 수 있어
#    **검사 전용 DB `callguard_e2e` 를 따로 만들고** 현재 `db/schema.sql`(29 테이블)을 넣는다. 볼륨은 지우지 않는다.
docker run -d --name callguard-postgres -e POSTGRES_DB=callguard -e POSTGRES_USER=callguard -e POSTGRES_PASSWORD=callguard-dev \
  -e TZ=Asia/Seoul -p 127.0.0.1:5432:5432 -v callguard-pg:/var/lib/postgresql/data postgres:17
docker exec callguard-postgres psql -U callguard -d callguard -c "CREATE DATABASE callguard_e2e"
docker exec -i callguard-postgres psql -U callguard -d callguard_e2e -q -v ON_ERROR_STOP=1 < db/schema.sql
#    그리고 지식베이스 조항을 `document` 테이블에 넣는다 — 없으면 추천 카드·콜 가드의 `source_doc_id` 가 전부 NULL 로 남는다(FK, B-6 출처).
#    UPSERT 라 여러 번 돌려도 된다. 99조항이어야 한다(2026-09-22 — 여권 4.23 추가)
DATABASE_URL=postgresql://callguard:callguard-dev@127.0.0.1:5432/callguard_e2e .venv/bin/python scripts/seed_documents.py

# ③ 로컬 env — 저장소의 .env 를 덮어쓰지 않는다. 검사용 파일을 따로 둔다 (값은 전부 개발용, 비밀 아님)
cat > /tmp/e2e.env <<'EOF'
DATABASE_URL=postgresql://callguard:callguard-dev@127.0.0.1:5432/callguard_e2e
ELASTICSEARCH_URL=http://localhost:9200
CUSTOMER_REF_HMAC_KEY=e2e-local-only-not-a-secret
CORE_API_URL=http://localhost:8000
# 쓰기 경로가 fail-closed 다(`decisions/120`) — 서버(INGEST_SERVICE_TOKEN)와 콜 미디에이터(CORE_API_TOKEN)에 **같은 로컬 전용 값**
INGEST_SERVICE_TOKEN=e2e-local-only-not-a-secret
CORE_API_TOKEN=e2e-local-only-not-a-secret
EOF

# ④ 서버 :8000   (.venv 에 uvicorn 이 없으면 .venv/bin/python -m pip install uvicorn==0.52.4 python-dotenv==1.2.3)
cd server && ../.venv/bin/python -m uvicorn main:app --env-file /tmp/e2e.env --port 8000 &
# ⑤ 콜 미디에이터 :8080 (루프백이라 토큰 불필요). node_modules 가 없으면 npm ci 먼저
cd services/call-mediator && npm ci && (set -a; source /tmp/e2e.env; set +a; node src/main.ts) &

curl -s localhost:8000/health   # spokes 에 masking·closure_gate·postcall·retrieval·trigger·call_guard·compliance
curl -s localhost:8080/health   # active_calls 0
```

`CUSTOMER_REF_HMAC_KEY` 가 없으면 `call.customer_id` 가 NULL 이라 **SYN-006 → SYN-007(같은 번호 재인입)** 이 이어지지 않는다.

## 2. 실행

```bash
.venv/bin/python scripts/persona_sim/e2e_check.py                       # dasan-v0 전 대본, 배속 4
.venv/bin/python scripts/persona_sim/e2e_check.py --only SYN-004 SYN-006 --speed 6
.venv/bin/python scripts/persona_sim/e2e_check.py --only SYN-004 --skip-replay --call-id syn-e2e-syn-004-20260918T1610   # 다시 판정만
.venv/bin/python scripts/persona_sim/e2e_check.py --dry-run             # 스택 없이 — 전부 ❌ 가 정상(판정 로직 확인용)
.venv/bin/python -m pytest scripts/persona_sim/tests -q                 # 판정 함수 단위 테스트(스택 없음)
```

- 대본마다 재생기(`services/call-mediator/scripts/replay_persona_call.ts`)를 `--watch --close` 로 subprocess 실행한다.
  **call_id 는 검사기가 정해 넘긴다**(`syn-e2e-<id>-<시각>`) — 재생기 출력은 파싱하지 않는다.
- **`--close` 는 상담원 토큰이 있어야 한다** (2026-09-22 정정). `POST /hub/calls/{id}/close` 가 `a866ff4`(`decisions/315`)부터
  **상담원 토큰 또는 서비스 토큰**을 요구한다(`server/apps/hub/dependencies/close_guard.py`). 로컬 서버에도 이제 서비스 토큰
  (`INGEST_SERVICE_TOKEN`)을 둔다(③ — fail-closed 라 없으면 쓰기 경로가 401). `--close` 는 그래도 상담원 토큰을 먼저 싣는다 — 이 문서의 앞 판은 토큰 없이 `--close` 가 되는 전제였고,
  09-22 QA 에서 401 로 **D-1·요약 초안 저장** 이 ❌ 였다.
  - 검사기가 **로컬 검사 DB 에 임시 상담원 토큰을 만든다**(`e2e/agent_token.py`) — 발급 API(`/admin/agent-tokens`)는 관리자
    구글 로그인이 있어야 해서, 서버가 토큰을 확인하는 방법 그대로(`agent_token.token_hash` = SHA-256 hex, 폐기 안 됨) 행을 넣는다.
    상담원 행은 `e2e-replayer`(role `agent`) 하나를 재사용한다. 원문은 재생기 환경변수 `CALL_AGENT_TOKEN` 으로만 넘기고
    (재생기는 헤더로만 싣는다), 검사가 끝나면 `revoked_at` 을 채워 폐기한다. **토큰 값은 화면·보고서·파일 어디에도 없다.**
  - **DB 와 서버(`--core-url`)가 둘 다 루프백일 때만** 만든다 — 운영 DB 에는 쓰지 않는다. 아니면 경고만 찍고 넘어간다.
  - 이미 `CALL_AGENT_TOKEN` 이 환경에 있으면 그것을 쓴다. 만들지 않으려면 `--no-agent-token`(그러면 D-1 이 ❌).
- **재생기는 마지막 턴을 확인하고 닫는다** (`w6-replay-last-turn`). 보낸 확정이 화자별로 전부 `/ws` 로 돌아온 뒤에야
  `{"type":"end"}` 를 보내고, `--final-timeout`(기본 20초) 안에 안 돌아오면 **경고 + 종료 코드 1** 이다 — 검사기가
  「재생기 종료 1」과 그 경고 줄을 찍는다. 저장 건수 판정(`왕복·API 확정 자막 수`)은 빠진 턴 번호를 적는다.
- 출력: `data/processed/persona-e2e/<YYYY-MM-DD-HHMM>.json` + `.md` (gitignore — 커밋하지 않는다). 종료 코드 0 = 전부 ✅.
- DB 는 `--database-url`(기본 위 ②의 `callguard_e2e`) 로 직접 읽는다. 못 붙으면 DB 판정만 건너뛰고 API 판정은 한다.

## 3. 판정 기준 (전부 규칙 — `e2e/judge.py`)

| 판정 | 무엇을 보나 | 실패 시 원인 갈래(1차 가설) |
|---|---|---|
| 왕복·API 확정 자막 수 · DB 행 수 · 화자 순서 | 대본 턴 수 == `/transcript` 확정 자막 == `transcript_segment` 확정 행. 모자라면 **빠진 턴 번호**를 적는다 | 배선 |
| **SEC-1·PII 원문 미잔존** | 턴 라벨의 PII 값(주민번호·전화·계좌·카드·인증번호·이름·주소)이 `/transcript` 본문·DB 본문에 **없다** — 구분자를 뺀 형태(`010 0000 0104` ↔ `01000000104`)도 본다. 라벨 없는 다른 턴에 같은 값이 남아도 잡는다 | 규칙 |
| **C-5·PII 글자 단위 잔존 0** (2026-09-22) | 라벨 값의 **글자가 하나라도** 가려지지 않고 남았는가 — 위 판정은 값 **전체**가 남을 때만 잡아서 SYN-017#12 「다나카 유이」→`*** *이` 가 ✅ 였다. 원문에서 라벨 자리마다 마스킹본 글자를 대조한다(서버 마스킹은 글자 수를 지키는 `*` 라 자리 그대로. 길이가 다르면 `SequenceMatcher` 로 맞춰 본다). 공백·구분자는 세지 않는다. 같은 값이 다른 턴 원문에 다시 나오면 그 턴도 본다 | 규칙 |
| C-6·콜 가드 라벨 재현 | `call_guard_flag`(segment, category) 를 «턴 × 갈래» 로 접어 라벨과 대조 — 누락·과잉 건별 | 규칙 |
| C-1~C-4·컴플라이언스 라벨 재현 | `compliance_flag`(segment, rule_code) 대조. 기대가 있는데 탐지 0 이면 배선(콜 미디에이터가 검사를 안 부름) | 배선 / 규칙 |
| F-2·절차 판정 존재 · 서류 목록 일치 · 마지막 판정 complete | `/record.closures` 중 대본 절차(`procedure.doc_ids` 의 TERM) 판정. 서류 이름은 괄호 부연을 떼고 대조 | 배선 / 대본 / 규칙 |
| F-2·필요서류 없음 | 서류 없는 대본(소관 아님 등)은 대본 절차의 판정이 0건이어야 한다 | 규칙 |
| **F-2·엉뚱한 절차 판정 0건** (2026-09-22) | `/record.closures` 중 대본 `procedure.doc_ids` **밖** 절차의 판정 — 1건이라도 있으면 ❌, 절차·판정을 나열한다. 전에는 대본 절차 판정만 골라 봐서 운영 SYN-010(서류 없음)이 `TERM-2.9` `incomplete` 를 냈는데도 ✅ 였다. 서류 없는 대본은 위 판정과 합쳐 «판정이 하나라도 있으면 ❌» 가 된다 | 규칙 |
| B·필요서류 카드 노출 | 추천 카드에 그 절차 조항이 떴는가. `source_doc_id` 가 비면 제목 앞 번호로 느슨히 본다 | 규칙 |
| D-1·요약 초안 저장 · call 행 · `stt_engine=synthetic-script` · `customer_id` | `/record.summary_text` · `call` 행 | 배선 |
| ⚠ 통화 후·ended_at/status · ⚠ B-6·카드 source_doc_id | **알려진 미구현** — ❌ 로 세지 않고 ⚠ 로 남긴다 | 알려진 미구현 |

실패는 지우지 않는다(절대 원칙 8). 보고서 아래에 원인 갈래별 목록이 따로 붙는다 — 대본을 규칙에 맞춰 고치지 않는다(README 「QA 페르소나 검수」와 같은 태도).

### 운영 확인에 쓰는 재생기 옵션 (검사기 밖)

- `--watch` 의 추천 줄에 **지연 구간**이 찍힌다 — `검색 NNNms · 생성 — · 내부 NNNms · e2e NNNms(STT 미경유)`(모양만 — 값은 그때그때 받은 것).
  콜 미디에이터가 서버 추천 응답을 펼쳐 방송하므로(`withE2eLatency`) `retrieval_ms`·`generation_ms` 가 `/ws` 에 있다.
  없는 값은 `—` 다(0 으로 적지 않는다). 합성 통화라 `e2e` 는 STT 를 뺀 값이다 — 성능 수치로 인용하지 않는다.
- `--save-ws <경로>` 는 `/ws` 프레임을 받은 그대로 jsonl 로 남긴다(마스킹본뿐). 운영에서 뜬 파일은 저장소 밖이나 gitignore 인 `data/` 에 둔다.

## 4. 말할 수 없는 것 (절대 원칙 10)

- **STT 정확도·A-5 WER** — 글자를 직접 흘렸다. 마스킹·콜 가드·검색 결과는 인식 오류 0 위의 **상한**이다
- **트리거 지연·p95** — 발화 시각은 재생기가 지어낸 값이다
- **D-5 통화 온도** — 오디오가 없다. `voice_outlier` 는 보지 않는다
- **성능** — «라벨이 재현됐다» 는 «규칙이 그 문구를 안다» 는 뜻이지 실제 통화에서의 재현율이 아니다. 골든셋 하네스(`scripts/run_eval.py`)와 섞지 않는다
- **블랙리스트 승인·베테랑 배정** — 사람(관리자)·서버 API 몫이라 재생기가 하지 않는다. SYN-007 은 SYN-006 요청이 승인된 뒤에만 의미가 있다

## 5. 끝낼 때

서버·콜 미디에이터 프로세스만 내린다. PG·ES 컨테이너와 볼륨은 남긴다 — `docker volume prune` 은 돌리지 않는다(2026-09-17 사고).
