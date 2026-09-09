# 401 — fired 필드를 프론트 계약에 추가

**날짜**: 2026-09-09
**상태**: 확정

## 맥락

서버 `RecommendResponse`(`server/apps/hub/adapter/inbound/api/schemas/recommendation_schema.py`)는
`fired: bool`을 **필수 필드**로 이미 보내고 있다 — "트리거 발동 여부. false 면 검색조차
하지 않았다"는 설명이 붙어 있고, `RecommendResult`(`recommendation_dto.py`)도 처음부터
"cards is None → 트리거 미발동. cards.no_relevant_document → 검색했으나 관련 문서 없음"을
구분하도록 설계돼 있었다(`w3-recommendation-pipeline` 티켓, 2026-08-27 완료).

그런데 `apps/dashboard/src/types/contract.ts`의 `RecommendationBatch`에는 이 필드가 없었다.
그 결과 프론트는 서버가 이미 구분해서 보내는 두 상태 —

- `fired: false` (검색조차 안 함)
- `fired: true, cards: []` (검색했으나 관련 문서 없음, B-6)

— 를 화면에서 똑같이 "관련 문서가 아직 없습니다"로만 보여주고 있었다. 서류 안내 대상이
아닌 민원(예: 단순 문의)과, 안내 대상인데 지식베이스에 문서가 없는 경우를 상담원이
구분할 수 없다는 뜻이다.

## 결정

`RecommendationBatch`에 `fired: boolean`(필수)을 추가한다. **서버 수정은 필요 없다** —
서버는 이미 이 필드를 보내고 있었고, 누락은 프론트 타입 쪽 문제였다.

프론트 파서(`lib/ws/realGatewayClient.ts`)와 스토어(`store/callStore.ts`)를 고쳐 세 상태를
구분해 화면에 반영한다:

| 상태 | 화면 |
|---|---|
| `fired: false` | "이 민원 유형은 서류 안내 대상이 아닙니다" |
| `fired: true, cards: []` | 기존 B-6 "관련 문서가 아직 없습니다" 그대로 재사용 |
| `fired: true, cards: [...]` | 기존 카드 목록 그대로 |

## 근거

1. **서버가 이미 구분해 보내는 정보를 프론트가 뭉개고 있었다.** `w3-recommendation-pipeline`
   티켓이 "앞의 둘을 같은 값으로 뭉개면 검색이 안 된 것과 찾았는데 없는 것을 구분할 수
   없다"고 명시적으로 경고한 지점이 그대로 프론트에서 재현됐다.
2. **계약 변경이 아니라 계약 반영 누락 수정이다.** 서버 스키마·DTO는 그대로 두고
   프론트 타입만 서버가 이미 보내는 값에 맞춘다.

## 되돌리는 법

`RecommendationBatch`에서 `fired` 필드를 빼고, 파서·스토어의 분기를 되돌린다.
서버 쪽 변경이 없었으므로 프론트 커밋만 되돌리면 된다.

## 승인

팀 논의 후 승인됨 (2026-09-09).
