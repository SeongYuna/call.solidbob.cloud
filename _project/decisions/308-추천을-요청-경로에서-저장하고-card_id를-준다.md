# 308 — 발동한 추천을 요청 경로에서 저장하고 카드에 `card_id` 를 싣는다

**날짜**: 2026-09-15
**작성**: 장민석 (브랜치 `server`)
**관련**: `POST /hub/cards/{card_id}/feedback`(E-1) · 테이블 `recommendation`·`recommendation_card`·`card_feedback` · 2026-09-14 미결 「`document` 테이블을 채우는 경로가 없다」

## 맥락

카드 피드백 API 는 있는데 **프론트가 부를 수 없었다** — 추천 응답 카드에 `card_id` 가 없다. 확인해 보니 id 를 빠뜨린 게 아니라
**추천을 한 번도 저장하지 않고 있었다**(`recommendation`·`recommendation_card` 에 쓰는 코드 0곳). `card_feedback.card_id` 는
`recommendation_card` 를 외래키로 잡으므로, 저장 없이는 줄 수 있는 id 가 존재하지 않는다. 프론트 `coreClient.ts` 도 이 사실을 주석으로 적어 두고 연결을 미뤘다.

## 선택지

| | 내용 | 걸리는 것 |
|---|---|---|
| ① **요청 경로에서 저장** | 발동 시 `recommendation` 1행 + 카드 행, 돌아온 id 를 응답에 | 실시간 경로에 DB 왕복이 는다 |
| ② 피드백 때 카드 내용을 같이 보내 그때 저장 | 추천 경로 무변경 | 클라이언트가 카드 내용을 서버에 되보낸다 — 조작 가능, 추천 이력이 안 남는다 |
| ③ 클라이언트 키(doc_id+title) | 서버 무변경 | `card_feedback` 외래키를 걷어야 한다 · 같은 조항 다른 추천을 구분 못 한다 |

## 결정

**①.**

- `RecommendationRecordPort.record(cards) -> card_id 튜플`(배열 순서 = rank). PostgreSQL 이면 저장, 없으면 로그 어댑터 → `card_id: null`
- **`internal_latency_ms` 는 저장 전에 잰다** — 4.1절 p95 채점 구간에 DB 왕복을 섞지 않는다(테스트로 고정)
- 미발동이면 저장하지 않는다. **「관련 문서 없음」(빈 카드)도 발동이라 `recommendation` 행은 남긴다** — 공백 리포트 재료
- `source_doc_id` 는 `document` 에 그 조항이 **있을 때만** 잇고 없으면 NULL — 운영 `document` 가 비어 있어도 23503 으로 추천 전체가 실패하지 않는다(콜 가드 저장과 같은 방식)
- 통화(`call`)가 없으면 **404** — 전사 저장(`CallNotStartedError`)과 같은 규칙. 게이트웨이는 통화 시작이 성공해야 채널을 여므로 정상 경로에서는 나지 않는다
- 응답 `CardSchema.card_id: string | null`

## 근거

- 피드백은 «어느 추천의 어느 카드» 를 가리켜야 품질 데이터가 된다 — 저장된 추천이 기준점이다. ②③은 그 기준점이 없다
- 추천 이력이 남으면 Recall·채택률을 운영 데이터로도 볼 수 있다(지금까지는 골든셋에서만)

## ⚠ 남는 것

- **실시간 경로에 INSERT 가 1 + 카드 수만큼 는다.** e2e 지연에 얼마나 더해지는지 **재지 않았다**(측정 불가 — 운영 부하 데이터 없음). 문제가 되면 `executemany`·비동기 적재로 바꾼다
- 추천마다 행이 쌓인다 — 보존 기간은 정하지 않았다
- 운영 `document` 가 비어 있는 동안 `recommendation_card.source_doc_id` 는 전부 NULL 이다(`seed_documents.py` 미실행)

## 되돌리는 법

1. `hub/dependencies/recommendation_provider.py` 에서 `record` 주입을 뺀다 → 저장 안 함, `card_id` 늘 null
2. 완전히 지우려면 `recommendation_record_port.py`·`log_recommendation_record_adapter.py`·`postgres/recommendation_repository.py`·`recommendation_record_provider.py` 와 `Card.card_id`·`CardSchema.card_id`, 라우터의 404 처리를 지운다
