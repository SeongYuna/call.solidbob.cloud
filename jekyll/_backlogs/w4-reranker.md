---
title: "리랭킹 — 병합 결과를 다시 세운다"
assignee: "류준"
role: "ai"
status: "todo"
sprint: 4
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

- [ ] 리랭커 적용 전/후 **MRR 변화**를 낸다 (Recall@5 는 후보 집합이 같으면 안 변하는 게 정상이다 — 변하면 버그다)
- [ ] 추가 지연을 잰다. **p95 ≤1,000ms 를 깨면 리랭킹을 끄는 쪽이 맞다** — 늦은 정답은 카드가 아니다
- [ ] 모델·후보 수(top-k)를 설정으로 둔다

## 주의

⚠ **리랭커는 `ai/` 에만 둔다.** `server/.importlinter` 계약 2 가 `server/` 안에서 `torch`·`transformers`
import 를 막는다([architecture.md §1](https://github.com/SeongYuna/call.solidbob.cloud/blob/main/docs/architecture.md)).
