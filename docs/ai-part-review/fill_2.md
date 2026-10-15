# fill_2 — KLUE 인식 모델 교체 후 지연 (발표자료 4장)

- 측정일: 2026-10-15 · 커밋: `63c4d41`(+ 미커밋 — NER 라벨 대응 · 스크립트) · 장치: 맥북 M5 **CPU**(torch 4스레드)
- 명령: `.venv/bin/python eval/review-2026-10/masking_latency.py rule|old|klue` — 구성마다 **별도 프로세스**(모델 한 번에 하나)
- 결과: `eval/review-2026-10/results/masking_latency.json` · 로그 `data/processed/fill-2026-10-15/fill2.log`

## 1. 교체가 연결됐는가

| | 상태 |
|---|---|
| 코드 | ✅ 연결 — `server/main.py::_wire_pii_ner` → `ai/provider.py::build_masking_provider` → `KoElectraNerTagger`(라벨 대응 `NAME→PER · ADDRESS→LOC` 추가). 어느 모델인지는 `PII_NER_MODEL_DIR` 하나가 정한다 |
| 평가 | ✅ 공식 하네스 3회 — C-5 누락 0 · 오분류 0 · 과잉 0.0 (n 40, P1~P7) · `data/processed/train-2026-10-15/eval-klue-ner.log` |
| **운영** | ❌ **아직 적용 안 됨** — 운영 시크릿은 옛 경로(`/models/koelectra-ner`), 이미지 0.1.49. 모델은 S3 에 올렸고 반영(0.1.50 · 메모리 5Gi)은 PR 머지 뒤 |

그래서 아래는 **운영과 같은 조립 코드로 로컬에서** 잰 값이다. 운영 노드 값이 아니다.

## 2. 왜 「722ms 와 같은 구간」 을 다시 재지 않았나

722ms 는 **트리거 발동 → 검색 → 카드 완성**(`recommendation_interactor.py` `internal_latency_ms`)이고, **마스킹·NER 은 그 구간에 없다** —
마스킹은 전사가 들어올 때(`POST /hub/transcripts`) 따로 돈다. NER 을 바꿔도 722ms 구간의 계산은 그대로다.
교체가 실제로 바꾸는 것은 **마스킹 단계 시간**이라 그것을 교체 전후로 잰다.

## 3. 결과 — 마스킹 단계, 발화 1건당

입력: 골든셋 C-5 고객 발화 **36건**(평균 23.9자) · AI Hub 다산 고객 발화 **500건**(시드 20261015, 평균 18.1자).

| 구성 | 콜드: 적재(예열 포함) | 콜드: 첫 호출 | 웜 p50 | **웜 p95** | 웜 최대 | 프로세스 RSS 증가 |
|---|---|---|---|---|---|---|
| 규칙만 | 3 ms | 0.1 ms | 0.0 ms | 0.0 ms | 0.2 ms | 0 MB |
| 규칙 + koelectra-ner (교체 전, 운영) | 2.3 초 | 13.9 ms | 12.4 / 11.8 ms | **24.7 / 22.1 ms** | 25.6 / 24.8 ms | +454 MB |
| **규칙 + korean-pii-ner-v3 (교체 후)** | 5.3 초 | 44.4 ms | 39.6 / 38.5 ms | **78.8 / 75.9 ms** | 89.9 / 81.9 ms | **+1,327 MB** |

(두 값 = 골든 36건 / AI Hub 500건)

- 교체 후 마스킹은 약 **3배 느려지고**(p95 +54 ms) 메모리는 **+0.87 GB** 더 든다 — 대신 STT 오류 20% 까지 누락 0(옛 모델 2건, `decisions/222`)이고 상업 이용 가능 라이선스다
- 세 모델(KoE5 + KLUE NER + 폭언 분류기)을 한 프로세스에 올리면 RSS 2,980 MB → 서버 파드 상한 3Gi → **5Gi**(`infra/k8s/base/server.yaml`)

## 한계

- 로컬 맥북 CPU 값이다 — 운영 c7i.2xlarge 에서 다시 잰다(배포 뒤 `/hub/transcripts` 응답 시간)
- 한 번 실행 · 단건 순차 호출 — 동시 요청은 재지 않았다
- 교체가 722ms 구간을 바꾸지 않는다는 것은 **코드로 확인**한 것이지 운영에서 잰 것이 아니다

## 발표자료에 붙일 한 줄

`교체 후 마스킹 단계 p95 76~79ms (이전 22~25ms · 로컬 CPU · 발화 36·500건) — 서버 내부 p95 722ms 구간(트리거→검색→카드)에는 마스킹이 없어 그 값은 그대로 · 운영 적용은 배포 대기`
