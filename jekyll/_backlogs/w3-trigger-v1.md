---
title: "트리거 판정 v1 — is_final 도착 기반 (B-1)"
assignee: "류준"
role: "ai"
status: "done"
sprint: 3
priority: 2
date: 2026-08-27
requirement:
  - "B-1"
paths:
  - "ai/apps/retrieval/domain/services/trigger.py"
  - "ai/apps/retrieval/adapter/outbound/is_final_trigger.py"
---

발화 → "지금 검색을 발동할 것인가". `TriggerPort` 를 구현한다.

## 왜 3주차 항목을 당겨왔나

**장민석 님 파이프라인의 남은 501 두 개가 검색·트리거**였다("`w2-naive-rag` 가 붙어야
내 파이프라인의 501 두 개가 풀린다"). 검색은 `w2-naive-rag` 에서 풀렸고, 트리거만 남으면
`server/` 담당이 파이프라인을 끝까지 흘려볼 수 없다. **규칙 계산뿐이라 크기가 작아** 당겼다.

## 판정 규칙

셋 다 만족할 때만 발동한다.

| 조건 | 왜 |
|---|---|
| `is_final` 이다 | interim 은 20초 발화에 **199건**(V4 실측). 매번 발동하면 검색이 초당 수십 번 돈다 |
| **고객** 발화다 | 문서가 필요한 시점은 고객이 질문을 끝냈을 때다. 상담원이 말하는 중에 화면을 바꾸면 방해다 |
| 내용이 있다 | 빈 문자열로 검색하면 의미 없는 상위 문서가 뜬다 |

자체 침묵 타이머를 만들지 않고 **STT 의 엔드포인팅 판단을 그대로 쓴다**(2026-08-25 팀 컨펌,
정성윤 제안). 침묵 임계값을 재려면 발화 간 침묵 길이가 필요한데 보유 데이터로는 잴 수 없었다.

## ⚠ 발동 시각(`at_ms`)은 지금 모형값이다

`TranscriptEvent` 에 **이벤트 도착 시각이 없다.** `utterance_end_ms`(발화가 끝난 시각)만 있다.
그래서 발동 시각을 **"발화 종료 + STT 최종 결과 지연(V4 실측 346ms)"** 으로 놓았다.

그 결과 이 구현으로 낸 지연 분포는 **상수 하나로 수렴한다** — p50 = p95 = 346,
적절 발동률 1.0. **숫자는 나오지만 측정이 아니다.**

그래서 이렇게 갈랐다:

| 경로 | 꽂는가 | 왜 |
|---|---|---|
| `server/main.py` (요청) | ✅ | 발동 여부(fire)는 **진짜 판정**이고, 이게 있어야 파이프라인이 흐른다 |
| `scripts/run_eval.py` (평가) | ❌ | 꽂으면 가짜 1.0 이 리포트에 남는다. 측정할 수 없는 것을 측정한 것처럼 쓰지 않는다(절대 원칙 10) |

**고칠 방법**: 콜 미디에이터가 도착 시각을 실어 보내고 포트가 그걸 받게 한다.
계약 변경이라 `server/` 와 합의가 필요하다 — [미결 항목](/open-items/)에 올렸다.
그때까지의 통로로 `IsFinalTrigger(now_ms=...)` 를 열어 뒀다.

## 완료 조건

- [x] `should_fire` / `fire_at_ms` — 순수 규칙, `domain/services/trigger.py`
- [x] `IsFinalTrigger` — `TriggerPort` 구현, `adapter/outbound/`
- [x] 테스트 19건 (규칙 11 + 포트 8)
- [x] `server/main.py` 에서 한 줄로 꽂을 수 있는 팩토리(`ai/provider.py` — 2026-08-27 `retrieval/` 밖으로 옮겼다)
- [ ] **`server/main.py` 실제 배선은 장민석 님 몫** — 아래 안내 참고

## 장민석 님께 — 배선 방법

`server/` 는 `ai/` 를 import 할 수 없지만(계약 2), **합성 루트 `main.py` 는 그 경계 밖**입니다.
`sys.path` 에 `ai/apps` 를 올리고 두 줄이면 됩니다.

```python
# server/main.py
AI = Path(__file__).resolve().parent.parent / "ai"
sys.path[:0] = [str(AI / "apps"), str(AI)]   # 앞은 retrieval·training, 뒤는 provider.py

from provider import build_retrieval_provider, build_trigger_provider
from hub.dependencies.retrieval_provider import get_retrieval_port
from hub.dependencies.trigger_provider import get_trigger_port

app.dependency_overrides[get_trigger_port] = build_trigger_provider()
SPOKES.append("trigger")

if settings.elasticsearch_configured:
    app.dependency_overrides[get_retrieval_port] = build_retrieval_provider(
        settings.elasticsearch_url, api_key=settings.elasticsearch_api_key
    )
    SPOKES.append("retrieval")
```

- 클라이언트는 **기동 시 한 번만** 만들어 재사용합니다(요청마다 만들면 연결 풀이 버려집니다)
- 설정은 **인자로 받습니다** — 스포크가 `os.environ` 을 직접 읽지 않습니다(`server/CLAUDE.md` 3번)
- `client=` 로 갈아끼울 수 있어 실제 ES 없이 배선 테스트가 됩니다(`ai/tests/test_spoke_provider.py`)

**배선을 제가 하지 않은 이유**: `server/main.py` 는 `server/` 소관입니다(`decisions/012`).
꽂기 쉬운 상태까지만 만들어 두는 게 경계에 맞다고 봤습니다 — 원하시면 제가 해도 됩니다.
