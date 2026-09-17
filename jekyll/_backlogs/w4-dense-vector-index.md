---
title: "dense_vector 인덱스 — 임베딩 검색을 붙인다"
assignee: "류준"
role: "ai"
status: "done"
sprint: 4
note: "09-15 dense 0.979/0.885 (BM25 0.833/0.659) · 운영 ES 에는 벡터 없음"
priority: 41
date: 2026-09-15
requirement:
  - "B-2"
paths:
  - "ai/apps/retrieval/*"
  - "scripts/index_knowledge_base.py"
---

## 무엇을

지식베이스 98조항을 **임베딩해 ES `dense_vector` 필드로 함께 적재**한다.
지금 인덱스는 `nori`(BM25) 한 겹뿐이다.

## 왜 — 4주차 목표인데 티켓이 0건이었다

[8주 마일스톤](/docs/08/) 4주차는 **「nori 인덱스 · dense_vector · RRF 병합 · 청킹 전략 3종 비교」**인데,
`w4-` 티켓 27건 중 여기 해당하는 것이 **하나도 없었다.** 4주차에 실제로 한 일(콜 미디에이터·블랙리스트·
관리자 로그인·배포)은 전부 로드맵에 없던 일이고, 로드맵에 적힌 일에는 티켓이 없었다.
2026-09-15 에 로드맵을 티켓으로 옮기면서 만든다 — **착수 전이다.**

## 모델은 이미 정해져 있다 — 다시 고르지 않는다

`_project/decisions/010` 이 **`KoE5`**(1024차원)로 확정했다. 같은 결정 기록이 적어 둔 실측 제약 둘 —

- **128토큰에서 truncation 이 실제로 일어난다.** 조항이 그보다 길면 뒤가 잘린 채 임베딩된다.
  98조항 중 몇 건이 걸리는지 **먼저 세고 그 수를 기록한다**(잘린 채로 재면 낮은 점수의 원인을 못 찾는다)
- 차원이 1024라 `dense_vector` 매핑도 1024다 — 바꾸면 재적재다

## 완료 조건

- [x] `index_knowledge_base.py` 가 `--to-es` 에서 본문과 임베딩을 **한 번에** 넣는다 (두 번 돌리지 않는다)
- [x] 128토큰 초과 조항 수를 세어 티켓 본문에 적는다
- [x] 임베딩 단독 Recall@5·MRR 을 골든셋 v1-150 으로 잰다 — **BM25 단독(0.833 / 0.659, `run_id=2`)과 나란히 적는다**
- [x] 수치에 측정일·커밋·명령·표본 수 네 가지가 붙는다(§5)

## 주의

**임베딩이 BM25 보다 나쁘게 나와도 그대로 적는다**(절대 원칙 8). 다음 티켓([RRF 병합](/backlog/w4-rrf-hybrid/))이
둘을 합치는 것이라, 단독 점수는 «합쳤을 때 무엇이 기여했는가» 를 읽는 기준선으로 쓰인다.

---

## 2026-09-15 — 임베딩 단독이 BM25 를 크게 앞선다: 0.833 → 0.979

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

- **dense 단독 94/96 · MRR 0.885** — BM25(80/96 · 0.659)가 놓친 16건 중 15건을 찾는다. 남은 오답 `GS-204`·`GS-205`
- 출처별: 팀 작성 84건 BM25 69 → dense 82 · **AI Hub 실제 전사 12건** 11 → 12. ⚠ 실제 전사가 12건뿐이라 «실제 통화에서도» 는 말할 수 없다

### 토큰 수 — 「128 토큰 truncation」 은 KoE5 의 상한이 아니었다

```
임베딩 입력 = 제목 + 본문 · "passage: " 접두어 포함 · 98조항
최대 189 토큰 · 128 초과 2건 · 512 초과(실제 잘림) 0건
```

⚠ 티켓이 적은 「128토큰에서 truncation 이 실제로 일어난다」는 `decisions/010` 이 **옛 후보 ko-sroberta-multitask**
(`max_seq_length: 128`)에 대해 적은 문장이다. KoE5 는 `model_max_length: 512` 라 **지금 지식베이스에서 잘리는 조항은 0건**이다.
128 초과 2건도 함께 적었다 — 티켓의 전제로 셌을 때의 값이다.

### 만든 것

- `koe5_embedder.py` — `query:`/`passage:` 접두어 · mean pooling + L2 정규화(`modules.json` 과 같은 계산, sentence-transformers 없이)
- `es_index.py` — `dense_vector` 1024 · cosine. **`embedding_dims` 를 줄 때만** 넣는다 — torch 없는 곳(운영 서버 파드, 런북 15-1)에서 적재해도 BM25 인덱스는 그대로 만들어진다
- `index_knowledge_base.py` — 모델·torch 가 없으면 BM25 만 적재하고 그 사실을 찍는다. 벡터 매핑 없는 기존 인덱스에 벡터를 넣으려 하면 멈춘다(ES 가 float 배열로 동적 매핑해 kNN 만 조용히 죽는다)
- `es_dense_retriever.py` — `num_candidates=100`(98조항이라 사실상 전수 비교 — 근사 오차를 비교에서 뺐다)
- ⚠ ES 9.5 가 1024차원에 **기본 `bbq_hnsw`(1비트 양자화)** 를 건다. 같은 벡터로 `bbq_hnsw`·`hnsw`·`flat` 을 따로 적재해 쟀더니 **셋 다 0.979 / 0.885** — 이 규모에서는 양자화가 결과를 바꾸지 않았다

⚠ **운영 ES 에는 벡터가 없다.** 이 인덱스는 로컬 것이다 → `_project/decisions/206` 「남는 것」
