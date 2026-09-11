# services/gateway — A-1~A-4 게이트웨이

오디오를 받아 Google STT 로 스트리밍 전사하고, 결과를 server 로 넘겨 **마스킹된 것만** 대시보드로 흘린다.
주 담당: 정성윤 (`_project/plan.md` 7.1절 · `_project/decisions/019`). 티켓: `jekyll/_backlogs/w4-gateway-streaming-stt.md`.

```
[오디오 생산자] ──WS /ingest (PCM16)──▶ gateway ──HTTP──▶ server  POST /hub/calls · /hub/transcripts · /hub/recommendations
                                          │ Google STT (ko-KR, interim)
[대시보드]      ◀──WS /ws (JSON)───────── gateway  ← 서버가 마스킹해 돌려준 응답만
```

## 실행

```bash
cd services/gateway
npm ci
npm start                       # ../../.env 를 읽는다. 셸 변수가 .env 보다 우선한다
```

server 가 `http://localhost:8000` 에 떠 있어야 한다(`cd server && uvicorn main:app --env-file ../.env`).
대시보드는 `apps/dashboard/.env.local` 에 `VITE_GATEWAY_WS_URL=ws://localhost:8080/ws` 를 넣으면 라이브 모드로 붙는다.

### 통화 흉내 — AI Hub 녹음 재생

```bash
node scripts/stream_wav.ts <파일.wav> --speaker customer --watch
```

실시간 속도로 흘려 넣고, `--watch` 가 **대시보드가 받는 것**을 찍는다. 스테레오면 0번 채널을 `agent`,
1번을 `customer` 로 갈라 연결 둘로 보낸다. 기본 30초까지만 보낸다(`--max-seconds`) — 쓴 만큼 과금된다.
자체 녹음은 쓰지 않는다(절대 원칙 7).

## 운영 (2026-09-11)

| | |
|---|---|
| 대시보드 | `wss://server.solidbob.cloud/gateway/ws?token=<뷰 토큰>` (`VITE_GATEWAY_WS_URL`) |
| 오디오 생산자 | `wss://server.solidbob.cloud/gateway/ingest?call_id=…&speaker=…` + `Authorization: Bearer <과금 토큰>` |
| 상태 | `https://server.solidbob.cloud/gateway/health` |

- **배포는 `main` 머지다.** `release.yml` 이 `infra/k8s/base/kustomization.yaml` 의 `callguard-gateway` newTag 로 굽는다.
  `src/`·`package*.json`·`infra/docker/gateway.Dockerfile` 을 고치면 **newTag 를 올려야** 한다 — 안 올리면 릴리스가 실패한다
- 매니페스트: `infra/k8s/base/gateway.yaml`. Ingress `/gateway` 경로는 이 서버가 스스로 뗀다(`PUBLIC_PREFIX`)
- 토큰은 배포가 인스턴스 안에서 만든다. 꺼내는 법·교체법: `infra/k8s/base/secret.example.yaml` ③
- 검증: 런북 19-1 (12·13번)
- ⚠ 뷰 토큰을 공개 대시보드 번들(Vercel env)에 넣으면 그 순간 비밀이 아니다 — 무작위 스캔만 막는다

## 설정 — `config.ts` 가 `process.env` 를 읽는 유일한 곳

| 키 | 없으면 |
|---|---|
| `GATEWAY_PORT` | 8080 |
| `CORE_API_URL` | `http://localhost:8000` (운영은 `http://callguard-server`) |
| `GOOGLE_APPLICATION_CREDENTIALS` | **키 파일 경로.** 파일이 없으면 `/ingest` 를 거절한다 — 가짜 STT 로 대신하지 않는다 |
| `STT_MAX_SECONDS_PER_DAY` · `_MONTH` | **거절한다(fail-closed).** 스트림은 끝을 미리 몰라서 캡 없이 열면 누가 끊기 전까지 과금된다 |
| `CORS_ALLOWED_ORIGINS` | 로컬 Vite 둘 — server 와 같은 키·같은 기본값. 대시보드 WS 의 `Origin` 을 대조한다 |
| `GATEWAY_INGEST_TOKEN` | `/ingest`(과금) 비밀. **없으면 이 머신(루프백) 접속만 받는다** |
| `GATEWAY_VIEW_TOKEN` | `/ws`(자막 보기) 토큰. **없으면 이 머신(루프백) 접속만 받는다** |

⚠ `GATEWAY_PORT`·`CORE_API_URL`·`GATEWAY_INGEST_TOKEN`·`GATEWAY_VIEW_TOKEN` 은 아직 `.env.example` 에 없다.
그 파일은 자격증명 보호 훅이 편집을 막아 사람이 채운다.

## 접속 제어 (`src/domain/access.ts`)

| 어디서 | 토큰 설정 안 함 | 토큰 설정함 |
|---|---|---|
| 이 머신(루프백) | 받는다 — 로컬 개발은 설정 없이 돈다 | 받는다 |
| 그 밖(쿠버네티스에서는 Traefik 을 거친 모든 접속) | **거절(401) — fail-closed** | 그 문의 토큰이 맞아야 받는다 |

- **토큰은 문마다 따로다.** `/ingest` 는 STT 과금을 쓰므로 `GATEWAY_INGEST_TOKEN` 이 **진짜 비밀**이고,
  `Authorization: Bearer` 헤더로만 받는다(URL 은 접근 로그·기록에 남는다).
  `/ws` 는 `GATEWAY_VIEW_TOKEN` 을 헤더나 `?token=` 으로 받는다 — 브라우저 WebSocket 은 헤더를 못 붙인다.
- ⚠ **뷰 토큰은 비밀이 아니다.** 대시보드는 공개 사이트라, 번들(`VITE_*`)에 넣는 순간 누구나 읽는다.
  무작위 스캔만 막는다. 그래서 둘을 갈랐다 — 뷰 토큰이 새도 과금 문은 안 열린다. 두 값을 같게 두면 기동 때 경고한다
- `/ws` 를 제대로 막으려면 **사람별 인증**(상담원 로그인)이 필요하다. 서버에도 아직 없다 — 이 토큰이 그걸 대신하지 않는다
- 루프백 판정은 `req.socket.remoteAddress` 로만 한다. `X-Forwarded-For` 는 믿지 않는다
- 토큰·거절된 요청의 쿼리는 로그에 남기지 않는다. `/health` 는 거르지 않는다(쿠버네티스 프로브)
- 생산자 스크립트는 환경변수 `GATEWAY_INGEST_TOKEN`·`GATEWAY_VIEW_TOKEN` 을 헤더로 보낸다(명령줄 인자로는 안 받는다)

## 계약

### `WS /ingest?call_id=&speaker=&sample_rate=&channels=` — 오디오 생산자

| 파라미터 | 값 |
|---|---|
| `call_id` | 영문·숫자·`_.:-` 1~40자. 테스트는 `test-` 로 시작한다 |
| `speaker` | `agent` · `customer` — **연결 하나 = 화자 하나**(채널 분리, A-2) |
| `sample_rate` | 8000 · 16000 · 22050 · 24000 · 44100 · 48000. 기본 16000 |
| `channels` | 이 통화에 붙을 채널 수 1·2. `call.channel_count` 로 간다 |

- 바이너리 프레임 = **PCM 16비트 리틀엔디언 모노**. 100ms 안팎으로 잘라 보낸다
- 끝낼 때 텍스트 `{"type":"end"}` → 남은 결과를 다 보낸 뒤 `1000` 으로 닫힌다. 그냥 끊어도 된다
- 거절·중단은 close 코드와 이유로 알린다 — `1008` 잘못된 요청·같은 화자 중복, `1013` STT 한도(COST-1), `1011` 서버·STT 문제

브라우저 마이크(①)는 `apps/dashboard` 몫이다 — `getUserMedia` → PCM16 변환 → 이 계약으로 붙는다.

### `WS /ws[?call_id=]` — 대시보드

받기만 한다. `call_id` 를 안 주면 모든 통화를 받는다. 메시지는 `realGatewayClient.ts` 가 이미 기다리는 형식이다.

```json
{"type": "transcript",     "payload": { /* POST /hub/transcripts 응답 그대로 — 값은 전부 문자열 */ }}
{"type": "recommendation", "payload": { /* POST /hub/recommendations 응답 그대로 */ }}
```

### `GET /health`

설정 여부·오늘 사용량·열린 통화 수. 주소·키 값은 싣지 않는다(SEC-2).

## 지키는 것

- **SEC-1** — 원문은 게이트웨이 → server 로만 간다. server 가 실패하면 그 결과는 **아무 데도 가지 않는다.**
  로그에는 번호·상태 코드만 남는다. 422 본문은 원문을 되돌려 주므로 읽지 않고 버린다
- **COST-1** — `data/processed/stt-usage.json` 을 `scripts/transcribe_batch.py` 와 **같은 파일·같은 형식**으로 쓴다.
  캡을 넘겼으면 새 채널을 열지 않고, 열린 채널도 캡에 닿으면 거기서 끊는다
- **A-1** 설정은 V4 측정(`scripts/test_stt_v4_streaming.py`)과 같다 — 바꾸면 그 지연 수치를 다시 잰다.
  구글 스트림 5분 한도는 교대로 넘긴다(4분 뒤 다음 final 에서, 4분 40초면 즉시)
- **A-4** 발화 구간은 구글 끝점 검출(`is_final`)이다. 따로 VAD 를 두지 않는다

## 하지 않는 것

- **모노 한 줄에 섞인 두 화자 분리(diarization)** — 채널 분리만 한다. 구글 화자 태그는 final 에만 붙고
  누가 상담원인지는 알려 주지 않는다. 잘못 붙이면 C-1~C-4(상담원)·C-6(고객) 방향이 뒤집힌다
- 판정 — 트리거·마스킹·추천은 전부 server 가 한다. 게이트웨이는 나르기만 한다
- 사람별 인증 — 위 토큰은 팀 공유 값이다. 상담원 로그인은 server 와 같은 미결 항목이다(「서버에 인증이 없다」)

## 검증

```bash
npm run typecheck && npm test      # 구글·서버 없이 돈다 (가짜 포트)
```

구조는 server 와 같은 헥사고날이다 — `domain/`(순수 규칙) ← `app/`(포트·배선) ← `adapters/`(구글·HTTP·WS·파일) ← `main.ts`(합성 루트).
TypeScript 라 import-linter 는 못 쓴다(`docs/architecture.md` §6 미결).
