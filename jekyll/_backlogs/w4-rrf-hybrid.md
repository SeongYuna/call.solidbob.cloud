---
title: "RRF 하이브리드 병합 — BM25 + 임베딩"
assignee: "류준"
role: "ai"
status: "done"
sprint: 4
note: "09-15 RRF 0.927/0.828 < dense 0.979/0.885 — 비채택(decisions/206)"
priority: 42
date: 2026-09-15
requirement:
  - "B-2"
depends_on:
  - "w4-dense-vector-index"
paths:
  - "ai/apps/retrieval/*"
---

## 무엇을

BM25(nori) 결과와 임베딩 결과를 **RRF(Reciprocal Rank Fusion)로 병합**해 `HybridRetriever` 를 완성한다.

## 어디서 병합하는가 — 이미 정해져 있다

**우리 코드에서 한다**(`_project/decisions/021`). ES 의 `rrf` 리트리버를 쓰지 않는다.
[3.1절 요구사항표](https://github.com/SeongYuna/call.solidbob.cloud/blob/main/.claude/rules/rfp-harness.md)의
「nori+dense_vector+RRF」는 **재료**를 가리키는 것이지 ES 기능을 쓰라는 뜻이 아니다.

## 완료 조건

- [x] `k`(RRF 상수)를 **고정값으로 박지 않고** 설정으로 둔다 — 60 은 관례지 측정값이 아니다
- [x] BM25 단독 · 임베딩 단독 · RRF **세 줄을 같은 표에** 낸다 (골든셋 v1-150)
- [x] 검수 기준 **Recall@5 ≥0.70(오류 없음)** 과 대조한다 — 지금 BM25 단독이 0.833 이므로 **떨어지면 그것이 결과다**
- [x] 내부 처리 **p95 ≤1,000ms**([4.1절](/docs/04/)) 안에 들어오는지 함께 잰다 — 두 번 검색하므로 지연이 는다

## 주의

**합쳤으니 좋아졌을 것이라고 적지 않는다.** 표본 96건에서 Recall@5 한 건은 약 0.01 이다 —
0.833 → 0.843 은 «한 건 더 맞았다» 이지 개선이 아니다. 차이를 적을 때 **건수로도 함께 적는다.**

---

## 2026-09-15 — 만들었고 쟀다. **채택하지 않는다** — dense 단독보다 낮다

```
측정일 2026-09-15 · 커밋 38f2fc3-dirty · 골든셋 v1-150 B 항목 n96 · 지식베이스 98조항 · 로컬 Darwin arm64
.venv/bin/python scripts/index_knowledge_base.py --to-es --recreate     # 본문 + KoE5 임베딩
.venv/bin/python scripts/compare_retrievers.py [--device mps]
결과 파일 data/processed/retrieval-compare/2026-09-15*.json (gitignore)

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

- **RRF 하이브리드 89/96 · MRR 0.828 — dense 단독(94/96 · 0.885)보다 5건 낮다.** BM25 가 놓친 16건 중 dense 가 찾은 15건 가운데
  **6건을 병합에서 도로 잃고**, BM25 만 맞힌 `GS-204` 1건을 되찾는다
- **k 문제가 아니다** — k=10·30·60·100 모두 89건. MRR 만 0.828~0.835 로 흔들린다(1위 한두 건 차이)
- 검수 기준 Recall@5 ≥0.70: 네 줄 전부 넘는다. p95: 하이브리드 58ms(CPU) — 두 검색을 `asyncio.gather` 로 동시에 부른다
- **k 를 골든셋에서 고르지 않았다.** 96건에서 가장 좋은 값을 박으면 골든셋에 맞춘 것이다 — 기본값은 관례 60 그대로, 설정으로 열어 뒀다

### 결정

**기본 구성은 dense + 리랭킹이다**(`_project/decisions/206`). `HybridRetriever` 는 지우지 않는다 — 지식베이스가 커지거나
번호·고유명사 질의가 늘면 BM25 가 기여할 수 있고, 같은 스크립트로 다시 잴 수 있어야 한다.
요구사항표의 「nori+dense_vector+RRF」는 **재료**를 적은 것이었고(티켓 본문 그대로), 재료를 다 써 본 결과가 이것이다.
