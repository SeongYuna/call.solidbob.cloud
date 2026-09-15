---
title: "RRF 하이브리드 병합 — BM25 + 임베딩"
assignee: "류준"
role: "ai"
status: "todo"
sprint: 4
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

- [ ] `k`(RRF 상수)를 **고정값으로 박지 않고** 설정으로 둔다 — 60 은 관례지 측정값이 아니다
- [ ] BM25 단독 · 임베딩 단독 · RRF **세 줄을 같은 표에** 낸다 (골든셋 v1-150)
- [ ] 검수 기준 **Recall@5 ≥0.70(오류 없음)** 과 대조한다 — 지금 BM25 단독이 0.833 이므로 **떨어지면 그것이 결과다**
- [ ] 내부 처리 **p95 ≤1,000ms**([4.1절](/docs/04/)) 안에 들어오는지 함께 잰다 — 두 번 검색하므로 지연이 는다

## 주의

**합쳤으니 좋아졌을 것이라고 적지 않는다.** 표본 96건에서 Recall@5 한 건은 약 0.01 이다 —
0.833 → 0.843 은 «한 건 더 맞았다» 이지 개선이 아니다. 차이를 적을 때 **건수로도 함께 적는다.**
