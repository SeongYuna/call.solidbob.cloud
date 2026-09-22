---
title: "테스트 위생 — F-2 검사가 늘 skip · 삭제된 도메인을 전제한 ES 통합 테스트 2건 · 공유 인덱스"
assignee: "류준"
role: "ai"
status: "todo"
sprint: 6
priority: 70
date: 2026-09-22
requirement:
  - "E-1"
  - "QUA-1"
paths:
  - "ai/tests/*"
  - "ai/apps/retrieval/tests/*"
---
> **정성윤이 09-22 저녁 최종 QA(류준 페르소나 4 + 검증 웨이브)·운영 확인 결과를 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

류준 최종 QA 에서 나온 셋(미결 「테스트·CI 위생」):

1. `ai/tests/test_eval_wiring.py` 가 옛 `v1-50` 을 읽어 **F-2 검사가 늘 skip** — 실제로는 99건 채점·통과다
2. ES 통합 테스트 2건이 삭제된 SHOP/HLT 도메인을 전제로 실패
3. 공유 인덱스 `callguard-kb-single` 을 지우고 벡터 없이 다시 만드는 테스트가 있다 — 로컬 dense 를 조용히 0건으로 만든다

CI server job 이 5건 skip(`elasticsearch`·`transformers` 없음)인 것은 별도로 적어 두기만 한다.

## 완료 조건

- [ ] 셋 다 고쳐 `cd ai && pytest` skip 사유에 v1-50·SHOP·HLT 가 없다
- [ ] 통합 테스트는 임시 인덱스 이름을 쓰고 끝나면 지운다
