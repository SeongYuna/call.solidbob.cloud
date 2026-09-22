---
title: "ai/ 모델 HTTP 표면 — GPU 인스턴스에서 도는 추론 서비스"
assignee: "류준"
role: "ai"
status: "cancelled"
sprint: 6
priority: 68
date: 2026-09-21
requirement:
  - "B-2"
  - "B-3"
  - "C-5"
depends_on:
  - "w6-gpu-model-instance"
paths:
  - "ai/apps/*"
---

## 무엇을

`decisions/121` 로 모델이 서버와 **다른 머신**에 간다. `ai/` 의 NER · 임베딩 · 리랭커 · 생성을
원격에서 부를 수 있게 **HTTP 표면**을 만든다.

## 왜 — 그리고 무엇이 바뀌는가

`decisions/024`·`105` 는 `ai/` 를 서버와 **같은 프로세스에 실리는 라이브러리**로 정했고
`ai/requirements.txt` 에 웹 프레임워크가 없다는 것이 그 전제였다. **그 전제가 깨진다** —
결정 기록(`2xx`)으로 남긴다. 포트(`RetrievalPort`·`MaskingPort` …)는 그대로 두고 어댑터만 바꾸는 구조다.

## 지켜야 할 것

- **의존 방향은 그대로 `ai → server` 한쪽이다.** 표면이 생겨도 `server` 가 `ai` 를 import 하지 않는다 — HTTP 로만 닿는다
- **판정은 규칙이, 설명만 LLM 이**(절대 원칙 9). 표면이 마스킹 «판정»을 모델 단독으로 돌려주지 않는다 — 규칙 + NER 두 겹 그대로
- 원문이 로그에 남지 않는다(SEC-1) — 요청 본문을 찍는 접근 로그를 켜지 않는다

## 완료 조건

- [ ] 표면 위치·프레임워크·인증을 결정 기록으로 남긴다
- [ ] 엔드포인트별 단위 테스트 + `.importlinter` 계약 3종 KEPT
- [ ] 로컬에서 서버 원격 어댑터([w6-server-remote-model-adapter](/backlog/w6-server-remote-model-adapter/))와 왕복 1건

## 2026-09-22 — `ai/` 쪽 표면 구현 (류준)

범위는 **`ai/` 만**이다(사용자 결정). `server/`·`infra/`·`.github/` 는 건드리지 않았다.

- 결정 기록: `_project/decisions/213` — 위치 `ai/apps/model_serving/`(inbound 어댑터) + 합성 루트 `ai/model_server.py` · FastAPI/uvicorn(서버와 같은 버전) · `MODEL_SERVICE_TOKEN` Bearer **fail-closed** · 오류 계약(401 · 503 `auth_not_configured`/`model_not_loaded`/`model_unavailable` · 500 · 422)
- 엔드포인트: `GET /health` · `POST /v1/ner/spans`(구간만 — 마스킹 판정 아님) · `/v1/embeddings` · `/v1/rerank` · `/v1/generation/cards`
- NER 구간 규칙을 `pii_ner` 한 함수(`detect_entities_with_rejoin`)로 모아 `LayeredMaskingAdapter` 와 표면이 같이 쓴다
- 테스트: 엔드포인트별 가짜 모델 단위 테스트 35 · 실제 소켓 왕복(uvicorn + `urllib`) · `server/` 가 표면을 import 하지 않는다는 AST 검사 · 실제 모델 스모크(`-m slow`)
- `ai/.importlinter` 에 `model_serving` 등록 — 3계약 KEPT

### 완료 조건 상태

- [x] 표면 위치·프레임워크·인증을 결정 기록으로 남긴다 — `decisions/213`
- [x] 엔드포인트별 단위 테스트 + `.importlinter` 계약 3종 KEPT
- [ ] 로컬에서 서버 원격 어댑터와 왕복 1건 — **서버 어댑터가 없다**(장민석, `w6-server-remote-model-adapter`). 그 자리는 테스트 안의 `urllib` 클라이언트가 대신 섰다. 그래서 `in-progress` 로 둔다

### 남은 것

- ⚠ CI `ai` job 이 fastapi·httpx·uvicorn 을 설치하지 않아 **표면 테스트는 CI 에서 건너뛴다**(의존 방향 검사만 돈다) — `test.yml` 한 줄
- `server/.importlinter` 계약 2 금지 목록에 `model_serving` 추가 — `server/` 소관
- `decisions/121` 질문 2(홉 지연)·3(비용·자동 중지)·5(6주차 기준선)는 열려 있다. **홉 지연은 미측정**이다

---

> **취소 (2026-09-22, 정성윤).** `_project/decisions/124` 로 모델을 전용 GPU EC2 가 아니라 운영 노드에 CPU 로 싣기로 했다. 전용 인스턴스·HTTP 표면·원격 어댑터가 필요 없어졌다. 이어받는 티켓: [w5-models-on-node](/backlog/w5-models-on-node/).
