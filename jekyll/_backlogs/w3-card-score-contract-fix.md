---
title: "카드 점수 필드명을 계약(similarity_score)에 맞춘다"
assignee: "정성윤"
role: "infra"
status: "done"
sprint: 3
priority: 3
date: 2026-09-09
depends_on:
  - "w1-interface-contract"
paths:
  - "server/apps/hub/adapter/inbound/api/schemas/recommendation_schema.py"
  - "server/apps/hub/app/dtos/recommendation_card_dto.py"
---

## 무엇을

서버 카드 응답의 점수 필드명 `score` 를 `similarity_score` 로 바꾼다.
HTTP 표면(`CardSchema`)과 내부 DTO(`Card`) 양쪽을 함께 맞춘다.

## 왜

**계약 정본 셋이 전부 `similarity_score` 인데 서버만 `score` 였다.**

| 출처 | 값 |
|---|---|
| `_project/decisions/003` 「결정 — 🟡 항목」 | `similarity_score` 로 통일 |
| `db/schema.sql:131` | `"similarity_score" REAL NULL` |
| [7.3절](/docs/07/) 카드 계약 JSON · v1→v2 변경표 | `similarity_score` |
| `server/.../recommendation_schema.py:32` | ~~`score`~~ ← 여기만 어긋났다 |

그 파일 독스트링이 *"응답 필드명은 7.3절 카드 계약 JSON 과 글자 단위로 같다"* 고
**선언해 놓고 어기고 있었다.**

**드러나지 않은 이유가 둘이다.**
① `test_recommendation_router.py` 의 「카드를 계약 형태로 돌려준다」 테스트가
`doc_id`·`summary`·`internal_latency_ms` 만 보고 **점수 필드명을 단언하지 않았다.**
② 배포된 대시보드가 mock 모드라 실서버 응답을 파싱한 적이 없다.

**⚠ 프론트는 이 필드가 없으면 카드를 통째로 버린다.** `realGatewayClient.ts:238`
`parseCard` 는 `similarity_score` 하나만 읽고 없으면 `null` 을 반환한다 —
에러 없이 사라진다. 실서버를 붙이는 순간 추천 카드가 화면에서 전부 없어졌을 것이다.

## 범위 밖 — 일부러 두는 것

- **`/hub/search` 의 `RetrievedDocSchema.score`**(`search_schema.py:21`). 7.3절 계약
  3종(전사·카드·종결)에 없는 엔드포인트이고, 검색 원문서 점수는 카드 유사도와 **다른 값**이다.
  `decisions/003` 이 *"RRF 원점수는 계약에 넣지 않는다"* 고 따로 정해 둔 영역이다.
- **`apps/dashboard`**. 이미 `similarity_score` 기준이라 고칠 것이 없다.

## 완료 조건

- [x] `CardSchema.score` → `similarity_score` (HTTP 표면)
- [x] `recommendation_router.py` 매핑 갱신
- [x] 내부 DTO `Card.score` → `similarity_score` + 독스트링의 「계약 v2 예시」 수정
- [x] `SnippetCardAdapter` 갱신 (`doc.score` 는 `RetrievedDoc` 이라 그대로)
- [x] `../ai/` grep — `Card` 참조 0건, 손댈 것 없음 (`server/CLAUDE.md` §5)
- [x] 테스트 4곳 갱신 + **라우터 테스트에 필드명 단언 추가** (재발 방지의 핵심)
- [x] `cd server && pytest` — 265 passed / 4 skipped
- [x] `lint-imports` — 계약 4종 KEPT
- [x] 역검증 — 일부러 `score` 로 되돌리면 새 단언이 실패하는 것 확인
- [ ] **장민석에게 통보** — `server/` 는 장민석 소관인데 PM 이 먼저 손댔다
- [ ] **조서희에게 회신** — 「둘 다 받는 방어 코드」는 저장소에 없다
- [ ] **운영 재배포** — 아래

## 남은 것 — 운영 재배포가 필요하다

**⚠ 처음엔 "재배포 불필요"로 적었는데 틀렸다. 런타임 응답만 보고 계약 표면을 놓쳤다.**

`/hub/recommendations` 가 trigger 스포크 부재로 **501** 인 것은 사실이나, 그것은
"카드가 아직 안 나온다"는 뜻일 뿐이다. **`https://server.solidbob.cloud/openapi.json`
은 501 과 무관하게 스키마를 공표하고 있고, 지금 거기에 `score` 가 실려 있다** —

```json
"CardSchema": { "properties": { ..., "score": {"type": "number"} },
                "required": ["title", "summary", "source", "score"] }
```

**`/docs` Swagger 가 프론트 담당이 붙일 때 읽는 바로 그 화면이다.** 이 어긋남이 애초에
퍼진 경로가 그것이므로, 고쳐 놓고 배포하지 않으면 같은 일이 반복된다.

**⚠ 같은 태그로 다시 구우면 배포가 조용히 안 먹는다.**

```yaml
image: seongyuna/callguard-server:0.1.0
imagePullPolicy: IfNotPresent      # ← 노드에 0.1.0 이 이미 있으면 새 이미지를 안 받는다
```

`kubectl rollout restart` 가 **성공한 것처럼 보이면서 옛 이미지가 계속 돈다.**
**태그를 `0.1.1` 로 올리고** `infra/k8s/base/kustomization.yaml:27` `newTag` 를 함께
고친다. 확인은 `/openapi.json` 의 `CardSchema` 에 `similarity_score` 가 뜨는지로 한다
— `/health` 는 이 변경에 대해 아무것도 말해주지 않는다.

⚠ 이 머신은 docker 데몬이 응답하지 않아 여기서는 굽지 못한다.
