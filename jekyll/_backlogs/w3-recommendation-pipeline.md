---
title: "추천 파이프라인 배선 — 트리거 → 검색 → 카드"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 3
priority: 2
date: 2026-08-27
requirement:
  - "B-0"
  - "B-1"
  - "B-2"
  - "B-4"
  - "B-6"
paths:
  - "server/apps/hub/app/use_cases/recommendation_interactor.py"
  - "server/apps/hub/adapter/inbound/api/v1/recommendation_router.py"
---

`server/` 의 본체. 전사 1건이 들어와 카드가 나올 때까지의 **순서를 정하는 곳**이다.

```
TranscriptEvent ─▶ TriggerPort(B-1) ─fire?─▶ DomainRoutingPort(B-0) ─▶ RetrievalPort(B-2·B-3) ─▶ GenerationPort(B-4~B-6)
```

기존 `transcript_ingest` 슬라이스는 마스킹까지만 하고 끝났다 — 그 뒤를 잇는 경로가 없었다.

## 판정을 하지 않는다

[절대 원칙 9](https://github.com/solidbob02/call.solidbob.cloud/blob/main/CLAUDE.md) 를 배선으로 고정했다.
인터랙터는 포트를 순서대로 부르기만 한다.

- 발동 여부를 `if` 로 다시 판단하지 않는다 — `TriggerDecision.fire` 를 그대로 따른다
- 검색 순서를 다시 매기지 않는다 — 리랭킹은 retrieval 스포크 몫
- 카드를 지어내지 않는다 — 생성이 빈 목록을 주면 「관련 문서 없음」(B-6)으로 그대로 나간다

## 세 가지 상태를 구분한다

|  | 뜻 |
|---|---|
| `fired: false`, `cards: null` | 트리거 미발동 — **검색조차 하지 않았다** |
| `fired: true`, `cards: []` | 발동했으나 「관련 문서 없음」(B-6) |
| `fired: true`, `cards: [...]` | 정상 |

앞의 둘을 같은 값으로 뭉개면 "검색이 안 돈 것"과 "찾았는데 없는 것"을 구분할 수 없다.

## 스포크가 없을 때의 기본값이 포트마다 다르다

| 포트 | 기본값 | 이유 |
|---|---|---|
| `TriggerPort` (B-1) | **501** | "항상 발동" 임시 구현을 두면 [6.1절](/docs/06/) 적절 발동률이 측정 대상에서 사라진다 |
| `RetrievalPort` (B-2) | **501** | 빈 목록은 「관련 문서 없음」과 구분되지 않는다 |
| `GenerationPort` (B-4) | **폴백(스니펫)** | [7.3절](/docs/07/)이 정의한 정식 모드다. 지어내지 않으므로 **환각이 구조적으로 0** |
| `DomainRoutingPort` (B-0) | **None(건너뜀)** | `decisions/007` 의 "신뢰도 낮으면 전 도메인 검색" 폴백이 항상 켜진 상태와 같다 |

`SnippetCardAdapter` 덕분에 **retrieval 하나만 꽂혀도 파이프라인이 끝까지 돈다.** generation 스포크가
붙은 뒤에는 이게 **환각 건수 비교의 기준선**이 된다.

## 지연 측정

`internal_latency_ms` 는 **트리거 발동 → 카드 완성** 구간이다([4.1절](/docs/04/) p95 ≤1,000ms 채점 재료).
시계를 주입 가능하게 해서 테스트가 고정값으로 검증한다. 발화 종료 → 화면 표시(e2e)는 콜 미디에이터·대시보드 몫.

## 완료 조건

`POST /hub/recommendations` 가 세 상태를 구분해 응답하고, trigger 미등록 시 501.
`cd server && pytest` 54개 통과 · `lint-imports` 계약 3종 KEPT.
