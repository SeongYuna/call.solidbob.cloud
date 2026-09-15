# 207 — B-4 서류 목록 생성 모델을 EXAONE-4.0-1.2B 에서 kanana-1.5-2.1b-instruct 로 바꾼다

- 날짜: 2026-09-15
- 작성: 류준 (`2xx` 번호대)
- 상태: 채택 (**운영 반영 전** — 아래 「운영 반영」)
- 영향: `ai/apps/generation/` · `ai/provider.py` · `server/main.py`(`_wire_generation`) · `server/core/config.py` · 런북 14-2(모델 받기)
- 관련: [010](010-AI-모델-구성-확정.md)(생성 EXAONE 확정 · kanana 를 6주차 대조군으로 지정) — **010 의 생성 모델 행을 뒤집는다**
- 티켓: `w6-card-generation` · `w6-hallucination-eval` · `w6-generation-model-compare`

---

## 맥락

`010` 은 생성 모델을 **지연**으로 골랐다(EXAONE 250토큰 2.0~2.1초, 첫 토큰 19~157ms). 환각은 **6주차 대조군 비교에서 재기로** 미뤘고,
대조군 kanana 는 그때 로컬에 받지 못했다. rev.5 가 B-4 를 「근거 기반 **서류 목록** 생성」으로 좁히면서 환각을 **규칙으로** 잴 수 있게 됐다 —
모델이 적은 서류 이름이 근거 조항 본문에 **문자 그대로** 있는가(`evaluation/metrics/generation.py`, 생성기 필터와 독립 구현).

## 측정

```
측정일 2026-09-15 · 커밋 38f2fc3-dirty · 골든셋 v1-150 B 항목 96문항 · 상위 1건 생성 · 로컬 Ollama 0.33.3 (Apple Silicon)
검색 결과는 파일로 고정해 세 조건에 같은 조항을 넣었다 (rerank-dense, data/processed/generation-eval/docs-rerank-dense.json)
.venv/bin/python scripts/eval_generation.py [--no-schema] [--model …]

조건                          원출력 환각 카드  환각 조각  목록 카드  「없음」  출력 토큰 평균  p50     p95
EXAONE-4.0-1.2B  + JSON 스키마      89/96         213       59        0        52          589ms   921ms
EXAONE-4.0-1.2B  스키마 없음        96/96         416       44        0        80(상한)    922ms   944ms
kanana-1.5-2.1b  스키마 없음        27/96          40       74       14        24          526ms   977ms
화면에 나간 카드의 환각 — 세 조건 모두 0 (규칙 필터가 근거 없는 이름을 버린다)
출처 표시율 — 세 조건 모두 100% (96/96)
```

- **같은 조건(스키마 없음)에서 kanana 가 원출력 환각 카드 96 → 27, 조각 416 → 40.** 스키마 강제를 켠 EXAONE(89)보다도 낮다
- **kanana 는 서류가 없는 조항에 「없음」(빈 배열)을 14번 답했다. EXAONE 은 0번** — 안내형 조항에서도 서류를 지어낸다
- EXAONE 은 지시를 따르지 않고 마크다운 설명문을 쓴다(출력이 상한 80토큰에 매번 닿는다). JSON 스키마로 모양을 강제해도 배열 안에 조항 제목·요약 문구를 넣는다
- 지연은 비슷하다. **같은 조건 p95 가 실행마다 150ms 쯤 흔들렸다**(EXAONE 스키마 761 → 921ms) — 로컬 머신 잡음이라 지연으로는 우열을 가리지 않는다

## 결정

**B-4 생성 기본 모델을 `kanana-1.5-2.1b-instruct`(Q4_K_M GGUF)로 바꾼다.** 비교는 스키마 없는 같은 조건에서 했고, 운영 설정도 그대로(스키마 없음) 간다.
EXAONE 은 대조 재측정용으로 이름만 남긴다(`EXAONE_MODEL`).

덤으로 **라이선스가 풀린다** — EXAONE 은 `EXAONE AI Model License 1.2 - NC`(비상업, 런북 14-5), kanana-1.5 는 **Apache-2.0** 이다(HF 카드 확인).

## 이 결정이 보장하지 않는 것

1. **「화면 환각 0」 은 거의 동어반복이다.** 생성기 필터와 채점기가 독립 구현이지만 **같은 개념(본문 문자 대조)** 이라, 필터가 통과시킨 것은 채점도 통과한다.
   의미 있는 수치는 **원출력 환각**이고, kanana 도 **27/96 은 검수 기준(150문항 중 5건 이하)에 한참 못 미친다.** 필터를 빼면 기준을 못 넘는다
2. **맞는 이름인데 절차에 안 맞는 서류**(초본 문의에 등본 서류)는 규칙으로 재지 않았고 사람이 세지도 않았다
3. 96문항이다 — 150 에 못 미친다. 환산하지 않는다
4. **GGUF 가 공식 배포본이 아니다.** `gchrisoh/kanana-1.5-2.1b-instruct-2505-Q4_K_M-GGUF` — llama.cpp 의 `gguf-my-repo` 로 공식 가중치
   (`kakaocorp/kanana-1.5-2.1b-instruct-2505`)를 변환한 것이다. 운영 전에 공식 가중치에서 직접 변환해 해시를 고정한다
5. **Ollama 0.33.3 에서 kanana 는 JSON 스키마 강제를 못 받는다**(`peg-native format` 500). 스키마 없이 운영한다 — 모양은 파서가 흡수한다
6. 처음 받았을 때 **stop 토큰이 빠져 `<|eot_id|>` 가 출력에 새어 나왔다.** Modelfile 에 넣지 않으면 같은 일이 난다(아래)

## 운영 반영 — 아직 안 했다

```bash
# 모델 등록 (로컬·운영 공통). models/ 는 gitignore — 가중치를 커밋하지 않는다
huggingface-cli download gchrisoh/kanana-1.5-2.1b-instruct-2505-Q4_K_M-GGUF kanana-1.5-2.1b-instruct-2505-q4_k_m.gguf --local-dir models/kanana-1.5-2.1b-instruct-gguf
cat > models/kanana-1.5-2.1b-instruct-gguf/Modelfile <<'M'
FROM ./kanana-1.5-2.1b-instruct-2505-q4_k_m.gguf
PARAMETER stop "<|eot_id|>"
PARAMETER stop "<|end_of_text|>"
M
cd models/kanana-1.5-2.1b-instruct-gguf && ollama create kanana-1.5-2.1b-instruct:q4_k_m -f Modelfile
```

- 서버는 **`OLLAMA_URL` 과 `GENERATION_MODEL` 이 둘 다 있어야** 생성을 켠다(`_wire_generation`). 런북 16-1 이 `OLLAMA_URL` 을 이미 주입하므로
  모델 이름 없이 켜지지 않게 했다 — 켜졌는지는 `/health` `spokes` 의 `generation`
- 런북 14-2 는 EXAONE 을 받는다. 운영 파드에서 위 절차로 바꾸는 것은 **인프라 작업이라 여기서 하지 않았다** — 정성윤 님과 정한다
- VRAM: Q4_K_M 2.3B ≈ 1.5GB 로 EXAONE(≈1.1GB)보다 크다 — 런북 11장 합계 표를 갱신해야 한다

## 되돌리는 법

`GENERATION_MODEL=hf.co/LGAI-EXAONE/EXAONE-4.0-1.2B-GGUF:latest` 로 두면 EXAONE 으로 돌아간다(프로바이더가 스키마를 켠다).
생성 자체를 끄려면 `GENERATION_MODEL` 을 비운다 → 스니펫 카드. 뒤집는 근거는 `scripts/eval_generation.py` 의 새 측정값이어야 한다.
