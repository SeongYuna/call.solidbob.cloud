---
title: "E2E 지연 측정 — 4.3절 예산이 실제로 지켜지는가"
assignee: "정성윤"
role: "infra"
status: "in-progress"
sprint: 7
priority: 71
date: 2026-09-15
requirement:
  - "B-1"
  - "A-1"
paths:
  - "services/call-mediator/src/*"
---

## 무엇을

발화 종료 → 카드 표시까지 **구간별 지연**을 운영 경로에서 잰다([4.3절](/docs/04/)).

## 잴 수 있게 된 지 얼마 안 됐다

2026-09-14 까지는 **못 쟀다.** `TranscriptEvent` 에 이벤트 도착 시각이 없어서
발동 시각을 「발화 종료 + 346ms」로 **모형화**하고 있었고, 그대로 채점하면
**p50 = p95 = 346 · 적절 발동률 1.0 이라는 가짜 만점**이 나왔다(절대 원칙 10).

09-14 에 콜 미디에이터가 `received_at_ms` 를 실어 보내고 트리거가 그것을 쓰도록 고쳤다
([w4-trigger-arrival-time](/backlog/w4-trigger-arrival-time/)) — **실시간 경로의
`trigger_at_ms` 는 이제 측정값이다.** 이 티켓은 그 값을 실제로 모으는 일이다.

⚠ **평가 하네스는 여전히 측정 불가다** — 골든셋에 도착 시각이 없다. 이 티켓은 **운영 경로**만 잰다.

## 구간

```
발화 종료 → STT 최종 결과 → 콜 미디에이터 수신 → 트리거 판정 → 검색 → 생성 → 브라우저 표시
```

**내부 처리 p95 ≤1,000ms**([4.1절](/docs/04/))는 그중 「트리거 판정 → 생성」 구간이다 —
전체 E2E 와 같은 숫자가 아니다. **두 수를 섞어 적지 않는다.**

## 완료 조건

- [ ] 구간별 p50·p95 를 **표본 수와 함께** 낸다 (한 통화로 잰 값을 p95 라고 부르지 않는다)
- [ ] 예산을 넘는 구간이 있으면 **그 구간을 지목한다** — 「느리다」가 아니라 「어디가 느리다」
- [ ] 측정일·커밋·명령·표본 수(§5)
- [ ] 리랭킹([w4-reranker](/backlog/w4-reranker/))·생성이 붙은 뒤의 값이어야 의미가 있다

---

## 설계 — 2026-09-20 (`_project/decisions/119`)

코드를 전수 확인해 **무엇이 있고 무엇이 없는지**를 구간별로 갈랐다.

| 구간 | 지금 | 할 일 |
|---|---|---|
| ① 발화 종료 → STT 최종 도착 | ✅ `received_at_ms − utterance_end_ms` | 그대로 쓴다 |
| ② 트리거 판정 | ✅ 실시간 경로는 측정값 | 그대로 |
| ③ 검색 | ❌ ②③④가 한 덩어리 | **쪼갠다** — `retrieval_ms` |
| ④ 생성 | ❌ 위와 같다 | **쪼갠다** — `generation_ms` |
| ②+③+④ | ✅ `internal_latency_ms`(저장까지 됨) | 뜻을 **「서버 내부 처리」**로 고정 |
| ⑤ 전송 → 방송 | ❌ | 콜 미디에이터가 `e2e_latency_ms` 를 채운다(방송 시각 − `utterance_end_ms`) |
| ⑥ 브라우저 렌더 | ❌ | **재지 않는다** — 결정 기록에 이유를 적었다 |

> **`e2e_latency_ms` 는 컬럼·DTO 가 있는데 아무도 채우지 않아 늘 NULL 이었다**(09-20 전수 grep).
> 서버가 모르는 값을 지어내지 않은 것이라 그 자체는 옳다 — **채울 주체를 정한 적이 없었을 뿐**이다.

## 할 일 (순서)

- [x] **서버**(2026-09-20, `0.1.19`) — `recommendation_interactor` 가 검색·생성을 **따로** 재어 `RecommendationCards` 에 싣는다.
      **스키마는 아직 안 고친다**(운영 `recommendation` 0행 · 마이그레이션은 사람 손). 방송·로그에만 싣는다
- [x] **콜 미디에이터**(2026-09-21, `0.2.2`) — 방송 직전에 `e2e_latency_ms = 방송 시각 − utterance_end_ms` 를 계산해 싣는다
- [ ] **측정** — `scripts/persona_sim/e2e_check.py` 가 구간별 p50·p95 를 **표본 수와 함께** 보고서에 낸다
- [ ] **보고** — 합성 통화는 **STT 를 안 거쳐 ①이 0** 이다. `source: synthetic` + 「STT 미경유」를 붙이고,
      ①은 V4 실측 **346ms** 를 더해 **「추정 E2E」**로 적되 **합산이 추정임을 같은 줄에** 쓴다(`decisions/209` 와 같은 규칙)
- [ ] 운영 통화가 쌓이기 시작하면 `retrieval_ms`·`generation_ms` 를 **컬럼으로 승격**(`generate_schema_docs.py` → 마이그레이션)

⚠ **하네스는 계속 「측정 불가」다** — 골든셋에 시계가 없다. 거기에 시각을 지어 넣지 않는다(절대 원칙 2).

## 준비 — 2026-09-21 코드 확인 (정성윤)

**`e2e_check.py` 는 지금 구간 값을 받을 수 없다.** 그래서 「측정」 칸의 첫 일은 수집 경로다.

- `e2e_check.py` 는 REST(`/hub/calls/{id}/transcript` · `/record`)와 **DB** 에서만 읽는다. DB 에는 `internal_latency_ms` 만 있다
- `retrieval_ms` · `generation_ms` 는 **DB 컬럼이 없다**(`decisions/119` ③) — 응답과 방송에만 실린다
- `e2e_latency_ms` 는 미디에이터가 **방송 직전**에 채운다(`call_registry.ts` 564~581줄). DB 값은 여전히 NULL 이다 — 서버가 방송 전에 저장하기 때문이다
- 방송을 받는 곳은 재생기의 `--watch` 다(`services/call-mediator/scripts/replay_persona_call.ts` — `/ws?call_id=` 를 연다)

**할 일 순서**
1. 재생기 `--watch` 가 받은 `recommendation` 메시지의 네 값(`internal_latency_ms` · `retrieval_ms` · `generation_ms` · `e2e_latency_ms`)을 JSONL 로 남긴다 — 류준 님 스크립트라 먼저 알린다
2. `e2e_check.py` 가 그 파일을 읽어 구간별 p50·p95 와 표본 수를 보고서에 낸다
3. 어디서 돌리나 — **운영 DB 는 이 머신에서 닿지 않는다**(RDS 는 VPC 안). 운영으로 재려면 DB 판정을 끄고 방송 값만 모으는 모드가 필요하다. 로컬 전체 스택이면 지금 그대로 된다
4. 모델이 운영 노드에 붙은 뒤 한 번 더 잰다 — 리랭커 지연이 여기서 처음 운영 값으로 나온다
