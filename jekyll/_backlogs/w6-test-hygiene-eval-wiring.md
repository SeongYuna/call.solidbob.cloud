---
title: "테스트 위생 — F-2 검사가 늘 skip · 삭제된 도메인을 전제한 ES 통합 테스트 2건 · 공유 인덱스"
assignee: "류준"
role: "ai"
status: "done"
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

- [x] 셋 다 고쳐 `cd ai && pytest` skip 사유에 v1-50·SHOP·HLT 가 없다
- [x] 통합 테스트는 임시 인덱스 이름을 쓰고 끝나면 지운다

## 2026-09-22 — 류준 착수·완료

1. **`ai/tests/test_eval_wiring.py` → `v1-150.json`.** F-2 skip 을 걷어냈다 — 이제 `closure_gate` 가 dict·`n > 0`·`absolute_rule_passed`·`accuracy == 1.0` 을 단언한다. C-5 도 `n > 0`·`miss_count == 0`. 골든셋이 지금도 자라고 있어 **표본 수는 단언하지 않는다.** 옛 `closure_gate == NO_SAMPLES` 단언(v1-150 에서는 설계상 깨진다)은 **F-2 항목을 뺀 부분집합**으로 옮겨 「잴 것 없음 ≠ 통과」 성질을 그대로 지킨다(`test_F2_케이스가_없으면_미구현도_통과도_아닌_잴것없음이다`).
2. **삭제 도메인 전제 2건 재작성**(`test_es_bm25_retriever.py`). 연기 테스트는 GS-259 「신혼부부 특별공급 자격이 어떻게 되나요」 → `DASAN-TERM-4.15` 1위(09-22 실측 1위/2위 점수비 4.37 — B 항목 중 격차 최대). 도메인 필터 테스트는 `dasan` 필터 결과 = 필터 없는 결과(전부 다산) **그리고** 색인에 없는 `finance` 로 좁히면 0건 — 필터가 실제로 질의에 걸리는지를 본다(앞 단언만으로는 필터가 무시돼도 통과한다).
3. **공유 인덱스 미접촉.** `es_index.index_names`·`index_name_for`·`create_indices`·`index_chunks` 에 `prefix`(기본값 `callguard-kb` — 운영 이름 불변)를 더했고, 두 통합 테스트 모듈은 `callguard-test-<uuid12>` 접두어로 만들고 teardown 에서 지운다. `callguard-kb-` 로 시작하지 않게 한 것은 `create_named_index` 와 같은 이유(운영 와일드카드 `callguard-kb-*` 에 섞이지 않게). 단위 테스트 2건이 접두어가 생성·적재·카운트까지 전파되는지 본다.

검증: `ELASTICSEARCH_URL=http://127.0.0.1:9200 pytest -o addopts="" -m integration` **12 passed, skip 0** — 쓴 인덱스는 `callguard-test-2e7d1c1fd351-single` · `callguard-test-ca616d68840e-{single,dasan}` 뿐이고 실행 뒤 `callguard-test-*` 는 0개, `callguard-kb-single` 은 uuid `sOsbV9ZhTm6hINWzFtW9Tg`·100건 그대로였다. 기본 `ai` 522 passed(skip 0) · lint-imports 3 kept · `server` 1301 passed 1 skipped.

**적어 두기만 한다(고치지 않음)** — CI `server` job 은 `elasticsearch`·`transformers` 가 설치돼 있지 않아 **5건 skip** 이다(로컬은 1건 — `test_main_pii_ner.py`, 모델 없음). 요청 경로의 ES·NER 배선 테스트가 CI 에서는 돌지 않는다는 뜻이다. 설치할지(이미지 크기·시간) 가짜 모듈로 대체할지는 미정.
