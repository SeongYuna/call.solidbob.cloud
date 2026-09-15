---
title: "생성 모델 대조군 — kanana-1.5-2.1b vs EXAONE-4.0-1.2B"
assignee: "류준"
role: "ai"
status: "done"
sprint: 6
note: "09-15 kanana 채택(decisions/207) — 같은 조건 원출력 환각 96→27 카드"
priority: 63
date: 2026-09-15
requirement:
  - "B-4"
depends_on:
  - "w6-card-generation"
paths:
  - "ai/apps/generation/*"
---

## 무엇을

`_project/decisions/010` 이 대조군으로 올려 둔 **`kanana-1.5-2.1b-instruct`** 를
**EXAONE-4.0-1.2B** 와 **환각 건수**로 붙인다.

## 왜 6주차인가

[미결 항목](/open-items/)이 **「6주차 환각 건수 비교에서 실측한다」**고 시점을 적어 뒀다.

## ⚠ 먼저 풀어야 할 것 — 모델을 아직 못 받았다

같은 미결 항목이 적고 있다: **Ollama 공식 라이브러리·`hf.co/kakaocorp/...` GGUF 둘 다 안 됐다.**
재시도가 먼저다. **못 받으면 이 티켓은 「대조군 확보 실패」로 닫고 그 사실을 적는다** —
비교하지 않은 것을 비교한 것처럼 쓰지 않는다(절대 원칙 10).

## 완료 조건

- [x] 같은 문항·같은 검색 결과·같은 프롬프트에서 두 모델을 돌린다
- [x] **환각 건수 · 출처 표시율 · 지연** 셋을 나란히 적는다 — 환각만 보면 느린 모델이 이긴다
- [x] 바꾸기로 하면 **결정 기록(`2xx`)** 을 쓴다. `decisions/010` 을 조용히 덮지 않는다

---

## 2026-09-15 — 받았고 쟀다. **kanana 로 바꾼다** (`decisions/207`)

### 모델을 받은 경로

- Ollama `hf.co/…` 경로는 이번에도 막혔다 — `realm host "huggingface.co" does not match original host "hf.co"`(Ollama 0.33.3). 08-26 의 실패도 같은 원인으로 보인다
- GGUF 를 직접 받아 `ollama create` 로 등록했다: `gchrisoh/kanana-1.5-2.1b-instruct-2505-Q4_K_M-GGUF`(llama.cpp `gguf-my-repo` 변환, base `kakaocorp/kanana-1.5-2.1b-instruct-2505`, Apache-2.0)
- ⚠ **처음엔 Modelfile 에 stop 토큰을 안 넣어 `<|eot_id|>` 가 출력에 새어 나왔다** — 그 상태로 잰 값은 버리고 고친 뒤 다시 쟀다
- ⚠ kanana 는 Ollama 의 JSON 스키마 강제를 못 받는다(500). 그래서 **대조는 스키마 없는 같은 조건**에서 했다

### 같은 문항 · 같은 검색 결과 · 같은 프롬프트

```
측정일 2026-09-15 · 커밋 38f2fc3-dirty · 골든셋 v1-150 B 96문항 · 상위 1건 생성 · 로컬 Ollama 0.33.3 (Apple Silicon)
검색 결과를 파일로 고정해 모든 조건에 같은 조항을 넣었다 (rerank-dense · data/processed/generation-eval/docs-rerank-dense.json)
.venv/bin/python scripts/eval_generation.py [--no-schema] [--model …]

조건                         원출력 환각 카드  환각 조각  목록 카드  「없음」  출력 토큰  p50    p95    출처 표시율  화면 환각
EXAONE-4.0-1.2B + 스키마         89/96          213        59        0       52     589ms  921ms   100%        0
EXAONE-4.0-1.2B 스키마 없음      96/96          416        44        0       80     922ms  944ms   100%        0
kanana-1.5-2.1b 스키마 없음      27/96           40        74       14       24     526ms  977ms   100%        0
```

- **원출력 환각: EXAONE 96 → kanana 27 카드**(같은 조건). 스키마를 켠 EXAONE(89)보다도 낮다
- **「없음」 답: kanana 14 · EXAONE 0** — EXAONE 은 서류가 없는 안내형 조항에도 서류를 지어낸다
- **출처 표시율**: 둘 다 100% · **지연**: p95 944 vs 977ms — 실행마다 150ms 흔들려 우열 없음. 느린 모델이 환각만 적은 것이 아니다(출력 토큰 80 vs 24)
- 라이선스도 풀린다: EXAONE NC(비상업) → kanana Apache-2.0

### 결정 기록

`_project/decisions/207` — `010` 의 생성 모델 행을 뒤집는다. 운영 반영(런북 14-2 모델 받기·VRAM 표)은 인프라 작업이라 하지 않았다.
