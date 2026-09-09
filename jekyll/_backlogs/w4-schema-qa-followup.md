---
title: "스키마 QA 후속 — F-2 전용 스키마·인입 경로 (server 소관)"
assignee: "장민석"
role: "ai"
status: "todo"
sprint: 4
priority: 9
date: 2026-09-09
requirement:
  - "F-2"
  - "A-1"
paths:
  - "server/apps/closure_gate/domain/value_objects/closure_rule.py"
  - "server/apps/hub/adapter/outbound/postgres/transcript_segment_repository.py"
---

## 무엇을

2026-09-09 스키마 QA(`_project/decisions/205`)에서 나온 것 중 **`server/` 소관**인 셋.
류준이 스키마·생성기까지만 고치고 넘긴다 — 담당 경계(`decisions/012`).

## ① `transcript_segment` UPSERT 를 복합키로 바꾼다 【치명 — 데이터 손상】

**스키마는 이미 고쳤다.** PK 가 `(call_id, segment_id)` 이므로
`transcript_segment_repository.py` 의 `ON CONFLICT ("segment_id")` 를
`ON CONFLICT ("call_id", "segment_id")` 로 바꿔야 한다. **안 고치면 UPSERT 가 터진다.**

재현했던 것(고치기 전):
```
 call_id | segment_id |         text
 c_001   |          1 | 수도요금이 왜 이래요   ← c_001 의 발화가 c_002 것으로 덮였다
```
`_DELETE_SPANS`·`_INSERT_SPAN` 도 `call_id` 를 함께 받아야 한다(`masking_event` 가 복합 FK).

## ② `call` 행을 만드는 코드가 없다 【치명 — 첫 통화에서 실패】

`INSERT INTO "call"` 이 **테스트 픽스처에만** 있다. `transcript_segment.call_id` 가
`call` 을 FK 로 참조하므로 **운영에서 첫 세그먼트를 넣는 순간 FK 위반**이다.
QA 중 실제로 부딪혔다.

인입 어댑터가 같은 트랜잭션에서 `INSERT INTO "call" (…) ON CONFLICT DO NOTHING` 을
먼저 치면 된다. `call.domain` 이 `NOT NULL CHECK` 라 그 값(`'dasan'`)을 정하는 곳도 필요하다.

## ③ `closure` 를 필요서류 체크리스트로 다시 만든다 【치명 — 다산에서 못 쓴다】

`decisions/201` 이 F-2 를 「필요서류 체크리스트」로 전용했는데 테이블은 아직
`closure_type CHECK('상품해지','보상','반품','교환')` + 금융·쇼핑 전용 BOOLEAN 10개다.
**다산 절차를 넣으면 CHECK 에 걸려 INSERT 가 거부되고**, 그 앞단에서
`closure_rule.py` 가 `UnknownClosureType` 으로 422 를 낸다.

**골든셋 F-2 케이스가 0건인 이유의 절반이 여기다** — 넣으면 하네스가 죽는다.

69종 서비스 × N종 서류를 BOOLEAN 컬럼으로 펼 수 없으므로 **헤더 + 항목** 2단 권고:

```
required_docs_check(check_id, call_id, procedure, verdict CHECK('complete','incomplete'),
                    source_doc_id FK document, decided_at)
required_docs_check_item(check_id, document_name, informed BOOLEAN, rank)
```

`missing` 은 `informed = false` 조회로 나오고, 「해당 없음」은 행이 없는 것이라
NULL 의 이중 의미가 사라진다. rev.5 의 `verdict` `blocked` → `incomplete` 도 여기서 함께.

## 완료 조건

- [ ] ① UPSERT 복합키 반영 — 통화 둘의 같은 순번 발화가 각각 남는 테스트
- [ ] ② `call` 행 생성 경로 — 첫 세그먼트가 FK 위반 없이 들어가는 테스트
- [ ] ③ 필요서류 체크리스트 스키마 + `closure_rule.py` 다산 절차 + DTO `incomplete`
- [ ] ③ 이후 골든셋에 F-2 케이스를 넣을 수 있다 → 류준에게 알린다
