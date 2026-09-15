---
title: "리랭킹 — 병합 결과를 다시 세운다"
assignee: "류준"
role: "ai"
status: "done"
sprint: 4
note: "09-15 MRR 0.885→0.919 (후보 5, p95 521ms CPU) · 후보 20 은 예산 초과"
priority: 43
date: 2026-09-15
requirement:
  - "B-3"
depends_on:
  - "w4-rrf-hybrid"
paths:
  - "ai/apps/retrieval/*"
---

## 무엇을

RRF 로 병합한 상위 후보를 **크로스 인코더로 다시 정렬**한다(B-3).

## 왜 순서가 중요한가 — MRR 이 여기서 움직인다

Recall@5 는 «5개 안에 있는가» 만 보지만 상담원은 **맨 위 카드부터** 읽는다.
지금 실측이 **Recall@5 0.833 인데 MRR 0.659** 다 — 찾기는 찾는데 **1위에 못 올리고 있다**는 뜻이다.
리랭킹이 겨냥하는 것이 정확히 이 간격이다.

## 완료 조건

- [x] 리랭커 적용 전/후 **MRR 변화**를 낸다 (Recall@5 는 후보 집합이 같으면 안 변하는 게 정상이다 — 변하면 버그다)
- [x] 추가 지연을 잰다. **p95 ≤1,000ms 를 깨면 리랭킹을 끄는 쪽이 맞다** — 늦은 정답은 카드가 아니다
- [x] 모델·후보 수(top-k)를 설정으로 둔다

## 주의

⚠ **리랭커는 `ai/` 에만 둔다.** `server/.importlinter` 계약 2 가 `server/` 안에서 `torch`·`transformers`
import 를 막는다([architecture.md §1](https://github.com/SeongYuna/call.solidbob.cloud/blob/main/docs/architecture.md)).

---

## 2026-09-15 — MRR 0.885 → 0.919 (후보 5). 후보 20 은 예산을 깬다

```
측정일 2026-09-15 · 커밋 38f2fc3-dirty · 골든셋 v1-150 B 항목 n96 · 지식베이스 98조항 · 로컬 Darwin arm64
.venv/bin/python scripts/index_knowledge_base.py --to-es --recreate     # 본문 + KoE5 임베딩
.venv/bin/python scripts/compare_retrievers.py [--device mps]
결과 파일 data/processed/retrieval-compare/2026-09-15*.json (gitignore)
리랭커 BAAI/bge-reranker-v2-m3 (다국어 크로스 인코더, Apache-2.0, 568M)

변형                          Recall@5   hits    MRR   top1 │ p95 CPU   p95 MPS
bm25 (run_id=2 와 같은 값)       0.833   80/96  0.659    51  │     4ms      7ms
dense (KoE5 kNN)                0.979   94/96  0.885    78  │    59ms     50ms
hybrid RRF k=60 cand=20         0.927   89/96  0.828    73  │    58ms     39ms
  k=10 / 30 / 100               0.927   89/96  0.835 / 0.828 / 0.828
rerank(bm25) cand=5             0.833   80/96  0.795    73  │   494ms    237ms
rerank(bm25) cand=20            0.906   87/96  0.860    79  │  1760ms   1068ms
rerank(dense) cand=5            0.979   94/96  0.919    84  │   521ms    289ms
rerank(dense) cand=20           0.979   94/96  0.921    84  │  1789ms   1317ms
rerank(hybrid) cand=5           0.927   89/96  0.886    82  │   529ms    373ms
rerank(hybrid) cand=20          0.979   94/96  0.916    83  │  1844ms   1197ms
```

- **후보 5(같은 5건을 다시 세움)** — Recall@5 가 **변하지 않았다**(bm25 80→80 · dense 94→94 · hybrid 89→89). 완료 조건의 불변식이 실측으로도 섰다.
  MRR: bm25 0.659→**0.795** · dense 0.885→**0.919** · hybrid 0.828→0.886. 1위 적중 dense 78→**84**건
- **후보 20** — 6위 이하를 끌어올려 Recall@5 가 **변하는 게 정상**이다(bm25 80→87). 그런데 dense 위에서는 94→94 로 이득이 없고
  MRR 0.921(+0.002)에 **p95 1,789ms(CPU)·1,317ms(MPS) — 예산을 깬다.** 티켓 조건대로 후보 20 은 쓰지 않는다
- 추가 지연(dense 대비, CPU p95): 59 → 521ms. ⚠ **로컬 값이다** — 운영 T4 는 Ollama 와 나눠 쓴다(런북 11장). 운영 p95 미측정

### ⚠ 새 모델을 들였다

`decisions/010` 은 리랭커를 고르지 않았다. 그래서 **결정 기록 `206` 을 썼다** — 010 을 덮는 것이 아니라 빈칸을 채운다.
**대조군을 재지 않았다** — 한국어 전용 리랭커와 붙여 본 적이 없다.

### 설정

`CrossEncoderReranker(inner, scorer, candidates=5)` · 운영은 `RETRIEVAL_RERANK_MODEL_DIR`(비우면 끔).
리랭커는 `ai/` 에만 있다 — `server/main.py` 는 `ai/provider.py` 팩토리를 부를 뿐 torch 를 import 하지 않는다(계약 2 KEPT).
