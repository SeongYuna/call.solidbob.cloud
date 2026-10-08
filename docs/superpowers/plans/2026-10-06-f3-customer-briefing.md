# F-3 통화 수신 전 고객 브리핑 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 「통화받기」 전에 같은 발신 번호의 지난 통화를 읽어 **통화 목적을 추정한 브리핑**을 `GET /hub/calls/{call_id}/briefing` 으로 돌려주고, 시연 대본으로 그 경로를 끝까지 태운다.

**Architecture:** 서버(`server/`)가 지난 통화 **사실을 규칙으로 모으고**(`BriefingFactsPort` · PostgreSQL), 규칙 브리핑 스포크(`server/apps/briefing`)가 기본 구현이다. 운영 모델이 있으면 `ai/apps/customer_briefing` 의 모델 어댑터가 규칙 브리핑 **위에** 목적 범주·세 줄을 얹고, 검사에 걸리면 규칙 결과로 내려간다. 재생기는 `--ring-seconds` 로 「벨 울리는 시간」을 만들고, 새 대본 묶음 `dasan-briefing` 과 채점 스크립트가 결과를 기록한다.

**Tech Stack:** Python 3.13 · FastAPI · psycopg(async) · pytest · import-linter · Ollama(kanana-1.5-2.1B, 기존 `OllamaChat`) · Node 24 TypeScript(`--experimental-strip-types`, 콜 미디에이터 재생기)

**Spec:** `_project/decisions/220-F-3-통화-수신-전-고객-브리핑.md` — 실행자는 이 계획과 함께 **반드시** 읽는다. 화면 카드는 범위 밖(`jekyll/_backlogs/w8-f3-briefing-card-ui.md`, 조서희).

## Global Constraints

- 응답 필드는 **전부 문자열**이다 — 숫자·불리언은 `_types.StrField` 로 문자열화, `None` 은 `null` 그대로(`server/apps/hub/adapter/inbound/api/schemas/_types.py`).
- 응답에 **`customer_id`·발신 번호·`display_hint` 를 싣지 않는다**(`decisions/304`·`322`).
- 목적 범주는 정확히 이 다섯이다: `재문의` · `후속 확인` · `서류 보완` · `컴플레인` · `신규 문의`.
- `status` 는 정확히 `ready` · `first_contact` · `unidentified` 셋이다. 없는 통화는 404.
- 라우터 인증은 `_READERS`(`require_reader`) — `/record`·`/transcript` 와 같다.
- 새 설정 키를 만들지 않는다 — 모델은 기존 `OLLAMA_URL` + (`POSTCALL_MODEL` 또는 `GENERATION_MODEL`)이 있을 때만 켠다.
- 모델 시간 상한 **10초**, 넘으면 규칙 브리핑. 모델은 **통화당 한 번**(캐시 · 동시 요청 합치기).
- 사실에 **`compliance_flag` 를 넣지 않는다**(상담원 기록이다).
- 금지 표현(부록 A-1): `안전합니다` `위험도` `등급` `점수` `%` `확실` `무조건` `보장` `틀림없` `위험 고객` `요주의`.
- `server/` 는 `ai/` 를 import 하지 않는다(server `.importlinter` 계약 2). `ai/` 는 `hub` 계약만 import 한다.
- 모든 새 파일 맨 위에 `# Requirement: F-3`(TS 는 `// Requirement: F-3`).
- 새 대본에 **폭언·성적 표현을 넣지 않는다**(`decisions/209` 4항). 개인정보는 실존 불가 가짜 값.
- 커밋은 이 계획 안의 커밋 단계에서만 브랜치 `ai` 에 한다. **푸시·PR 은 하지 않는다**(사용자 지시 대기).

## Review Focus

- 지난 통화가 있는데 **요약이 모두 `NULL`**(통화를 `/close` 하지 않고 끝냄) — `ready` 이고, 규칙 브리핑은 유형·미완료 절차만으로 줄을 만들며 없는 요약을 지어내지 않는다 → Task 1 테스트 `test_rule_lines_without_summaries`.
- 화면이 **같은 통화 브리핑을 두 번 동시에** 부른다(재렌더·`started` 재수신) — 모델은 한 번만 불린다 → Task 3 테스트 `test_concurrent_requests_compose_once`.
- 모델이 **목록 밖 범주**(`서류보완` 띄어쓰기 없음, `민원`)나 **재료에 없는 숫자**를 낸다 — 규칙 결과로 내려가고 `source` 가 `rule` → Task 4 테스트 `test_out_of_list_category_falls_back`·`test_invented_digit_falls_back`.
- **이번 통화 자신**이 지난 통화로 섞인다 — `call_id <>` 와 `started_at <` 둘 다 걸어 빼고, 같은 시각 통화도 빠진다 → Task 2 테스트 `test_prior_calls_exclude_current`.
- 응답 JSON 어디에도 고객 ID 가 **새지 않는다**(중첩 `evidence` 포함) → Task 3 테스트 `test_response_has_no_customer_identity`.

---

## 파일 구조

| 파일 | 책임 |
|---|---|
| `server/apps/hub/app/dtos/customer_briefing_dto.py` (생성) | 계약 DTO — 사실·결과·범주 목록 |
| `server/apps/hub/app/ports/output/briefing_facts_port.py` (생성) | 지난 통화 사실 읽기 포트 |
| `server/apps/hub/app/ports/output/customer_briefing_port.py` (생성) | 사실 → (목적, 줄) 포트 |
| `server/apps/hub/app/ports/input/customer_briefing_use_case.py` (생성) | 유스케이스 인터페이스 |
| `server/apps/hub/app/use_cases/customer_briefing_interactor.py` (생성) | 상태 분기 · 캐시 · 동시 요청 합치기 |
| `server/apps/briefing/domain/services/briefing_rules.py` (생성) | 규칙 목적·규칙 줄(순수 파이썬) |
| `server/apps/briefing/adapter/outbound/rule_briefing_adapter.py` (생성) | `CustomerBriefingPort` 규칙 구현 |
| `server/apps/hub/adapter/outbound/postgres/briefing_facts_repository.py` (생성) | `BriefingFactsPort` PostgreSQL 구현 |
| `server/apps/hub/adapter/inbound/api/schemas/customer_briefing_schema.py` (생성) | HTTP 스키마(문자열화) |
| `server/apps/hub/adapter/inbound/api/v1/customer_briefing_router.py` (생성) | `GET /hub/calls/{call_id}/briefing` |
| `server/apps/hub/dependencies/customer_briefing_provider.py` (생성) | 포트·유스케이스 조립, 캐시 싱글턴 |
| `server/main.py` (수정) | 라우터 등록 · `_wire_briefing_model` · 스포크 이름 |
| `server/.importlinter` (수정) | `briefing` 등록 |
| `ai/apps/customer_briefing/domain/services/briefing_checks.py` (생성) | 모델 출력 검사 · 프롬프트 |
| `ai/apps/customer_briefing/adapter/outbound/model_briefing_adapter.py` (생성) | 모델 어댑터(규칙 위에 얹기) |
| `ai/provider.py` (수정) | `build_briefing_provider` |
| `ai/.importlinter` (수정) | `customer_briefing` 등록 |
| `services/call-mediator/scripts/replay_persona_call.ts` (수정) | `--ring-seconds` |
| `scripts/persona_sim/dasan-briefing/SYN-301~306.json` (생성) | 대본 고객 셋 |
| `scripts/persona_sim/briefing_check.py` (생성) | 지난 통화 쌓기 → 벨 → 브리핑 → 채점 |

---

### Task 1: 계약 DTO · 포트 · 규칙 브리핑 스포크

**Files:**
- Create: `server/apps/hub/app/dtos/customer_briefing_dto.py`
- Create: `server/apps/hub/app/ports/output/briefing_facts_port.py`
- Create: `server/apps/hub/app/ports/output/customer_briefing_port.py`
- Create: `server/apps/briefing/__init__.py`, `server/apps/briefing/domain/__init__.py`, `server/apps/briefing/domain/services/__init__.py`, `server/apps/briefing/adapter/__init__.py`, `server/apps/briefing/adapter/outbound/__init__.py`, `server/apps/briefing/tests/__init__.py`, `server/apps/briefing/tests/domain/__init__.py`
- Create: `server/apps/briefing/domain/services/briefing_rules.py`
- Create: `server/apps/briefing/adapter/outbound/rule_briefing_adapter.py`
- Modify: `server/.importlinter`
- Test: `server/apps/briefing/tests/domain/test_briefing_rules.py`

**Interfaces:**
- Produces:
  - `hub.app.dtos.customer_briefing_dto`: `BRIEFING_PURPOSES: tuple[str, ...]`, `PriorCall`, `BriefingFacts`, `BriefingPurpose`, `BriefingComposition`, `CustomerBriefing`, `BriefingCallNotFound`
  - `hub.app.ports.output.briefing_facts_port.BriefingFactsPort.collect(call_id: str) -> BriefingFacts | None` (async)
  - `hub.app.ports.output.customer_briefing_port.CustomerBriefingPort.compose(facts: BriefingFacts) -> BriefingComposition` (async)
  - `briefing.domain.services.briefing_rules`: `rule_purpose(facts) -> BriefingPurpose`, `rule_lines(facts) -> tuple[str, ...]`, `facts_text(facts) -> str`
  - `briefing.adapter.outbound.rule_briefing_adapter.RuleBriefingAdapter(CustomerBriefingPort)`

- [ ] **Step 1: DTO 를 만든다** — `server/apps/hub/app/dtos/customer_briefing_dto.py`

```python
# Requirement: F-3
"""통화 수신 전 고객 브리핑 계약 (`decisions/220`). 나르기만 한다 — 판정·문장 만들기는 포트 뒤에 있다.

**고객 ID 를 담지 않는다.** `BriefingFacts.customer_identified` 는 «식별했는가» 만 말한다(`304`·`322`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

BRIEFING_PURPOSES: tuple[str, ...] = ("재문의", "후속 확인", "서류 보완", "컴플레인", "신규 문의")


@dataclass(frozen=True)
class PriorCall:
    call_id: str
    started_at: datetime
    inquiry_type: str | None
    summary_text: str | None          # 마스킹본에서 만든 D-1. 통화 후 처리 전이면 None
    summary_confirmed: bool
    open_follow_ups: tuple[str, ...] = ()          # status draft·confirmed 의 action_text
    incomplete_procedures: tuple[str, ...] = ()    # 절차별 마지막 판정이 incomplete 인 procedure
    call_guard_categories: tuple[str, ...] = ()    # insult·threat·sexual·distress — 문구는 싣지 않는다


@dataclass(frozen=True)
class BriefingFacts:
    call_id: str
    customer_identified: bool
    prior_calls: tuple[PriorCall, ...] = ()   # 최근순, 최대 5
    blacklisted: bool = False                 # 적용 중인 등록이 있다는 사실만


@dataclass(frozen=True)
class BriefingPurpose:
    category: str   # BRIEFING_PURPOSES 중 하나
    text: str
    source: str     # "model" | "rule"


@dataclass(frozen=True)
class BriefingComposition:
    purpose: BriefingPurpose
    lines: tuple[str, ...]


@dataclass(frozen=True)
class CustomerBriefing:
    call_id: str
    status: str   # ready | first_contact | unidentified
    prior_call_count: int
    purpose: BriefingPurpose | None
    lines: tuple[str, ...]
    evidence: tuple[PriorCall, ...]
    open_follow_ups: int
    call_guard_categories: tuple[str, ...]
    blacklisted: bool
    generated_at: datetime
    extra: dict = field(default_factory=dict, compare=False)  # 측정용(모델 소요 시간 등) — 응답에 싣지 않는다


class BriefingCallNotFound(LookupError):
    """그런 통화가 없다."""
```

- [ ] **Step 2: 포트 두 개를 만든다**

`server/apps/hub/app/ports/output/briefing_facts_port.py`:

```python
# Requirement: F-3
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.customer_briefing_dto import BriefingFacts


class BriefingFactsPort(ABC):
    """이번 통화의 고객으로 **이번 통화보다 앞선** 통화 사실을 모은다. 없는 통화면 None."""

    @abstractmethod
    async def collect(self, call_id: str) -> BriefingFacts | None: ...
```

`server/apps/hub/app/ports/output/customer_briefing_port.py`:

```python
# Requirement: F-3
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.customer_briefing_dto import BriefingComposition, BriefingFacts


class CustomerBriefingPort(ABC):
    """사실 → 목적 추정 + 브리핑 줄. 지난 통화가 1건 이상일 때만 불린다. 모델 추론일 수 있어 async."""

    @abstractmethod
    async def compose(self, facts: BriefingFacts) -> BriefingComposition: ...
```

- [ ] **Step 3: 실패하는 규칙 테스트를 쓴다** — `server/apps/briefing/tests/domain/test_briefing_rules.py`

```python
# Requirement: F-3
from datetime import datetime, timezone

from briefing.domain.services.briefing_rules import facts_text, rule_lines, rule_purpose
from hub.app.dtos.customer_briefing_dto import BRIEFING_PURPOSES, BriefingFacts, PriorCall

T = datetime(2026, 10, 5, 5, 2, tzinfo=timezone.utc)  # KST 10-05 14:02


def _facts(*calls, blacklisted=False):
    return BriefingFacts(call_id="now", customer_identified=True, prior_calls=tuple(calls), blacklisted=blacklisted)


def _call(**kw):
    base = dict(call_id="p1", started_at=T, inquiry_type="일반행정", summary_text="고객이 위임 등본 발급을 문의했다.",
                summary_confirmed=True)
    base.update(kw)
    return PriorCall(**base)


def test_incomplete_procedure_wins():
    p = rule_purpose(_facts(_call(incomplete_procedures=("DASAN-TERM-4.1",), open_follow_ups=("회신",))))
    assert p.category == "서류 보완" and p.source == "rule"


def test_follow_up_before_complaint():
    p = rule_purpose(_facts(_call(open_follow_ups=("담당 부서 회신",), call_guard_categories=("insult",))))
    assert p.category == "후속 확인"


def test_call_guard_means_complaint():
    assert rule_purpose(_facts(_call(call_guard_categories=("insult",)))).category == "컴플레인"


def test_plain_history_is_reinquiry():
    assert rule_purpose(_facts(_call())).category == "재문의"


def test_only_latest_call_decides():
    older = _call(call_id="p0", incomplete_procedures=("DASAN-TERM-4.1",))
    latest = _call(call_id="p1")
    assert rule_purpose(_facts(latest, older)).category == "재문의"


def test_category_always_in_list():
    for f in (_facts(_call()), _facts(_call(open_follow_ups=("x",)))):
        assert rule_purpose(f).category in BRIEFING_PURPOSES


def test_rule_lines_at_most_three_and_no_forbidden_words():
    lines = rule_lines(_facts(_call(open_follow_ups=("담당 부서 회신",), incomplete_procedures=("DASAN-TERM-4.1",),
                                    call_guard_categories=("insult",)), blacklisted=True))
    assert 1 <= len(lines) <= 3
    joined = " ".join(lines)
    for bad in ("위험", "요주의", "점수", "%", "확실"):
        assert bad not in joined


def test_rule_lines_without_summaries():
    lines = rule_lines(_facts(_call(summary_text=None, inquiry_type=None, incomplete_procedures=("DASAN-TERM-4.1",))))
    assert lines and all("None" not in line for line in lines)
    assert "DASAN-TERM-4.1" in " ".join(lines)


def test_facts_text_carries_summaries_and_dates_but_no_ids():
    text = facts_text(_facts(_call()))
    assert "위임 등본" in text and "10-05" in text and "p1" not in text
```

- [ ] **Step 4: 실패를 확인한다**

Run: `cd server && ../.venv/bin/python -m pytest apps/briefing/tests -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'briefing'`

- [ ] **Step 5: 규칙을 구현한다** — `server/apps/briefing/domain/services/briefing_rules.py`

```python
# Requirement: F-3
"""규칙 브리핑 — 모델이 없거나 모델 출력이 검사에 걸렸을 때 나가는 브리핑(`decisions/220` 2절). 순수 파이썬.

목적은 **가장 최근 지난 통화 하나**로 고른다. 우선순위: 서류 보완 > 후속 확인 > 컴플레인 > 재문의.
문장은 사실을 옮길 뿐 평가하지 않는다(부록 A-1).
"""

from __future__ import annotations

from datetime import timedelta, timezone

from hub.app.dtos.customer_briefing_dto import BriefingFacts, BriefingPurpose, PriorCall

_KST = timezone(timedelta(hours=9))
_CALL_GUARD_WORDS = {"insult": "언성", "threat": "위협 발언", "sexual": "부적절한 발언", "distress": "위기 신호"}


def _day(call: PriorCall) -> str:
    return call.started_at.astimezone(_KST).strftime("%m-%d")


def rule_purpose(facts: BriefingFacts) -> BriefingPurpose:
    latest = facts.prior_calls[0]
    if latest.incomplete_procedures:
        return BriefingPurpose("서류 보완", f"지난 통화({_day(latest)})에서 서류 안내가 끝나지 않은 절차가 있어 보완 문의로 보입니다", "rule")
    if latest.open_follow_ups:
        return BriefingPurpose("후속 확인", f"지난 통화({_day(latest)})에서 약속한 후속조치를 확인하려는 것으로 보입니다", "rule")
    if latest.call_guard_categories:
        return BriefingPurpose("컴플레인", f"지난 통화({_day(latest)})에서 불만 신호가 있어 같은 건의 재민원으로 보입니다", "rule")
    kind = latest.inquiry_type or "지난"
    return BriefingPurpose("재문의", f"{kind} 문의를 다시 하는 것으로 보입니다", "rule")


def rule_lines(facts: BriefingFacts) -> tuple[str, ...]:
    latest = facts.prior_calls[0]
    lines = [f"같은 번호로 걸려 온 지난 통화 {len(facts.prior_calls)}건 — 최근 {_day(latest)} {latest.inquiry_type or '유형 미정'}"]
    if latest.incomplete_procedures:
        lines.append("안내가 끝나지 않은 서류 절차: " + ", ".join(latest.incomplete_procedures))
    elif latest.open_follow_ups:
        lines.append("마치지 않은 후속조치: " + latest.open_follow_ups[0])
    elif latest.summary_text:
        lines.append(latest.summary_text[:80])
    signals = [_CALL_GUARD_WORDS[c] for c in latest.call_guard_categories if c in _CALL_GUARD_WORDS]
    if signals:
        lines.append("지난 통화에 " + "·".join(signals) + "이 있었습니다")
    elif facts.blacklisted:
        lines.append("블랙리스트 적용 중")
    return tuple(lines[:3])


def facts_text(facts: BriefingFacts) -> str:
    """모델에게 주는 재료 — 날짜·유형·요약·후속조치·미완료 절차·콜 가드 범주. **통화 ID·고객 ID 는 넣지 않는다.**"""
    out = []
    for i, c in enumerate(facts.prior_calls, start=1):
        out.append(f"[지난 통화 {i}] {_day(c)} · 유형 {c.inquiry_type or '미정'} · 요약 {c.summary_text or '없음'}")
        if c.open_follow_ups:
            out.append("  후속조치: " + "; ".join(c.open_follow_ups))
        if c.incomplete_procedures:
            out.append("  서류 안내 미완료 절차: " + ", ".join(c.incomplete_procedures))
        if c.call_guard_categories:
            out.append("  고객 쪽 신호: " + ", ".join(c.call_guard_categories))
    if facts.blacklisted:
        out.append("블랙리스트 적용 중")
    return "\n".join(out)
```

`server/apps/briefing/adapter/outbound/rule_briefing_adapter.py`:

```python
# Requirement: F-3
from __future__ import annotations

from hub.app.dtos.customer_briefing_dto import BriefingComposition, BriefingFacts
from hub.app.ports.output.customer_briefing_port import CustomerBriefingPort

from ...domain.services.briefing_rules import rule_lines, rule_purpose


class RuleBriefingAdapter(CustomerBriefingPort):
    """규칙 브리핑. 모델 어댑터(`ai/apps/customer_briefing`)의 폴백이기도 하다."""

    async def compose(self, facts: BriefingFacts) -> BriefingComposition:
        return BriefingComposition(purpose=rule_purpose(facts), lines=rule_lines(facts))
```

- [ ] **Step 6: import-linter 에 `briefing` 을 등록한다** — `server/.importlinter`

`[importlinter] root_packages` 에 `briefing` 추가 · 계약 1 `containers` 에 `briefing` · 계약 2 `source_modules` 에 `briefing` · 계약 3 `source_modules` 에 `briefing.domain` · 계약 4 `source_modules` 에 `briefing.domain` · `hub-app-knows-no-spoke` 의 `forbidden_modules` 에 `briefing`. 머리말 「등록됨」 줄에 `briefing(F-3 규칙 브리핑, 2026-10-06 decisions/220)` 을 덧붙인다.

- [ ] **Step 7: 통과를 확인한다**

Run: `cd server && ../.venv/bin/python -m pytest apps/briefing/tests -q && PYTHONPATH=apps ../.venv/bin/lint-imports --config .importlinter`
Expected: 9 passed · `Contracts: 5 kept, 0 broken.`

- [ ] **Step 8: 커밋**

```bash
git add server/apps/hub/app/dtos/customer_briefing_dto.py server/apps/hub/app/ports/output/briefing_facts_port.py \
  server/apps/hub/app/ports/output/customer_briefing_port.py server/apps/briefing server/.importlinter
git commit -m "code(f3): 브리핑 계약 DTO·포트 + 규칙 브리핑 스포크 (decisions/220)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: 지난 통화 사실 저장소 (PostgreSQL)

**Files:**
- Create: `server/apps/hub/adapter/outbound/postgres/briefing_facts_repository.py`
- Test: `server/apps/hub/tests/adapter/outbound/test_briefing_facts_repository.py`

**Interfaces:**
- Consumes: `BriefingFactsPort`, `BriefingFacts`, `PriorCall` (Task 1) · `ConnectionFactory` (`hub/adapter/outbound/postgres/connection.py`)
- Produces: `PostgresBriefingFactsRepository(connect: ConnectionFactory)` — `BriefingFactsPort` 구현

- [ ] **Step 1: 가짜 커서로 실패하는 테스트를 쓴다** — 같은 디렉터리의 기존 테스트(`test_call_record_repository.py`)가 쓰는 가짜 커넥션 모양을 그대로 따른다. 그 파일을 먼저 읽고 같은 헬퍼를 쓴다.

```python
# Requirement: F-3, SEC-1
"""SQL 이 무엇을 묻는지와 행 → DTO 변환을 본다. 실제 스키마 대조는 integration 테스트."""

from datetime import datetime, timedelta, timezone

import pytest

from hub.adapter.outbound.postgres.briefing_facts_repository import PostgresBriefingFactsRepository

T = datetime(2026, 10, 6, 5, 0, tzinfo=timezone.utc)


class _Cursor:
    def __init__(self, script):
        self.script = list(script)   # [(sql_fragment, rows | row)] 순서대로
        self.calls = []

    async def execute(self, sql, args=None):
        self.calls.append((sql, args))

    async def fetchone(self):
        return self.script.pop(0)

    async def fetchall(self):
        return self.script.pop(0)


class _Ctx:
    def __init__(self, obj):
        self.obj = obj

    async def __aenter__(self):
        return self.obj

    async def __aexit__(self, *a):
        return False


class _Conn:
    def __init__(self, cur):
        self.cur = cur

    def cursor(self):
        return _Ctx(self.cur)


def _repo(script):
    cur = _Cursor(script)
    return PostgresBriefingFactsRepository(lambda: _Ctx(_Conn(cur))), cur


@pytest.mark.asyncio
async def test_unknown_call_is_none():
    repo, _ = _repo([None])
    assert await repo.collect("x") is None


@pytest.mark.asyncio
async def test_unidentified_customer_skips_history():
    repo, cur = _repo([(None, T)])
    facts = await repo.collect("now")
    assert facts.customer_identified is False and facts.prior_calls == ()
    assert len(cur.calls) == 1


@pytest.mark.asyncio
async def test_prior_calls_exclude_current():
    p1 = ("p1", T - timedelta(days=1), "일반행정", "요약", T - timedelta(hours=20))
    repo, cur = _repo([
        ("hmac", T),                     # 이번 통화
        [p1],                            # 지난 통화
        [("p1", "회신 드리겠습니다")],     # 후속조치
        [("p1", "DASAN-TERM-4.1", "incomplete")],  # 절차별 마지막 판정
        [("p1", "insult")],              # 콜 가드
        (True,),                         # 블랙리스트
    ])
    facts = await repo.collect("now")
    sql, args = cur.calls[1]
    assert '"call_id" <> %s' in sql and '"started_at" < %s' in sql and args == ("hmac", "now", T)
    assert facts.customer_identified and facts.blacklisted
    pc = facts.prior_calls[0]
    assert pc.call_id == "p1" and pc.summary_confirmed is True
    assert pc.open_follow_ups == ("회신 드리겠습니다",)
    assert pc.incomplete_procedures == ("DASAN-TERM-4.1",)
    assert pc.call_guard_categories == ("insult",)


@pytest.mark.asyncio
async def test_completed_procedure_is_not_incomplete():
    p1 = ("p1", T - timedelta(days=1), None, None, None)
    repo, _ = _repo([("hmac", T), [p1], [], [("p1", "DASAN-TERM-4.1", "complete")], [], (False,)])
    facts = await repo.collect("now")
    assert facts.prior_calls[0].incomplete_procedures == ()
    assert facts.prior_calls[0].summary_confirmed is False


@pytest.mark.asyncio
async def test_first_contact_has_no_followup_queries():
    repo, cur = _repo([("hmac", T), [], (False,)])
    facts = await repo.collect("now")
    assert facts.customer_identified and facts.prior_calls == ()
    assert len(cur.calls) == 3   # 이번 통화 · 지난 통화 · 블랙리스트
```

`server/pytest.ini` 에 `asyncio_mode` 가 무엇인지 먼저 확인하고, `auto` 면 `@pytest.mark.asyncio` 를 빼도 된다(기존 테스트와 같은 방식을 따른다).

- [ ] **Step 2: 실패를 확인한다**

Run: `cd server && ../.venv/bin/python -m pytest apps/hub/tests/adapter/outbound/test_briefing_facts_repository.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현한다** — `server/apps/hub/adapter/outbound/postgres/briefing_facts_repository.py`

```python
# Requirement: F-3, SEC-1
"""BriefingFactsPort 의 PostgreSQL 구현 — 읽기만 한다. 담긴 글자는 마스킹본에서 나온 것뿐이다(SEC-1).

**`compliance_flag` 는 읽지 않는다** — 상담원 기록이지 고객 정보가 아니다(`decisions/220` 1절).
절차 판정은 같은 절차에 여러 번 쌓이므로 **절차별 마지막 판정**만 본다.
"""

from __future__ import annotations

from collections import defaultdict

from hub.app.dtos.customer_briefing_dto import BriefingFacts, PriorCall
from hub.app.ports.output.briefing_facts_port import BriefingFactsPort

from .connection import ConnectionFactory

MAX_PRIOR_CALLS = 5

_CURRENT = 'SELECT "customer_id", "started_at" FROM "call" WHERE "call_id" = %s'
_PRIOR = """
SELECT "call_id", "started_at", "inquiry_type", "summary_text", "summary_confirmed_at"
FROM "call"
WHERE "customer_id" = %s AND "call_id" <> %s AND "started_at" < %s
ORDER BY "started_at" DESC LIMIT 5
"""
_FOLLOW_UPS = """
SELECT "call_id", "action_text" FROM "follow_up_action"
WHERE "call_id" = ANY(%s) AND "status" IN ('draft', 'confirmed') ORDER BY "created_at", "id"
"""
_LATEST_CLOSURES = """
SELECT DISTINCT ON ("call_id", "procedure") "call_id", "procedure", "verdict" FROM "closure"
WHERE "call_id" = ANY(%s) ORDER BY "call_id", "procedure", "decided_at" DESC, "closure_id" DESC
"""
_CALL_GUARD = 'SELECT DISTINCT "call_id", "category" FROM "call_guard_flag" WHERE "call_id" = ANY(%s) ORDER BY "call_id", "category"'
_BLACKLISTED = """
SELECT EXISTS (SELECT 1 FROM "blacklist_entry"
               WHERE "customer_ref" = %s AND "released_at" IS NULL AND "expires_at" > now())
"""


class PostgresBriefingFactsRepository(BriefingFactsPort):
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    async def collect(self, call_id: str) -> BriefingFacts | None:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_CURRENT, (call_id,))
                current = await cur.fetchone()
                if current is None:
                    return None
                customer_id, started_at = current
                if customer_id is None:
                    return BriefingFacts(call_id=call_id, customer_identified=False)
                await cur.execute(_PRIOR, (customer_id, call_id, started_at))
                prior_rows = await cur.fetchall()
                ids = [r[0] for r in prior_rows]
                follow_ups, closures, guards = [], [], []
                if ids:
                    await cur.execute(_FOLLOW_UPS, (ids,))
                    follow_ups = await cur.fetchall()
                    await cur.execute(_LATEST_CLOSURES, (ids,))
                    closures = await cur.fetchall()
                    await cur.execute(_CALL_GUARD, (ids,))
                    guards = await cur.fetchall()
                await cur.execute(_BLACKLISTED, (customer_id,))
                (blacklisted,) = await cur.fetchone()

        fu: dict[str, list[str]] = defaultdict(list)
        for cid, text in follow_ups:
            fu[cid].append(text)
        incomplete: dict[str, list[str]] = defaultdict(list)
        for cid, procedure, verdict in closures:
            if verdict == "incomplete":
                incomplete[cid].append(procedure)
        cg: dict[str, list[str]] = defaultdict(list)
        for cid, category in guards:
            cg[cid].append(category)
        prior = tuple(
            PriorCall(call_id=cid, started_at=at, inquiry_type=itype, summary_text=summary,
                      summary_confirmed=confirmed_at is not None,
                      open_follow_ups=tuple(fu[cid]), incomplete_procedures=tuple(incomplete[cid]),
                      call_guard_categories=tuple(cg[cid]))
            for cid, at, itype, summary, confirmed_at in prior_rows
        )
        return BriefingFacts(call_id=call_id, customer_identified=True, prior_calls=prior, blacklisted=bool(blacklisted))
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd server && ../.venv/bin/python -m pytest apps/hub/tests/adapter/outbound/test_briefing_facts_repository.py -q`
Expected: 5 passed

- [ ] **Step 5: 실제 스키마로 한 번 돌린다(integration)** — `server/CLAUDE.md` §4. 같은 파일에 `@pytest.mark.integration` 테스트 하나를 더한다: `integration_settings` 픽스처(`server/conftest.py`)로 연결해 `customer` 1행 · 통화 2건(지난/이번) · `follow_up_action` 1행 · `closure` 2행(같은 절차 incomplete → complete 순서) 을 넣고, `collect("이번")` 의 `incomplete_procedures == ()` 와 `open_follow_ups` 를 확인한 뒤 넣은 행을 지운다. 로컬 DB 는 `docs/…` 가 아니라 `scripts/persona_sim/E2E.md` 의 `callguard_e2e`(127.0.0.1:5434)를 **새로 만든 DB 이름**으로 쓴다.

Run: `cd server && CALLGUARD_TEST_DATABASE_URL=postgresql://callguard:callguard-dev@127.0.0.1:5434/callguard_brief_it ../.venv/bin/python -m pytest -m integration apps/hub/tests/adapter/outbound/test_briefing_facts_repository.py -q`
(먼저 `docker exec callguard-postgres psql -U callguard -d callguard -c "CREATE DATABASE callguard_brief_it"` 후 `db/schema.sql` 적용)
Expected: 1 passed

- [ ] **Step 6: 커밋**

```bash
git add server/apps/hub/adapter/outbound/postgres/briefing_facts_repository.py server/apps/hub/tests/adapter/outbound/test_briefing_facts_repository.py
git commit -m "code(f3): 지난 통화 사실 저장소 — 절차별 마지막 판정 · 이번 통화 제외 (decisions/220)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: 유스케이스 · 캐시 · 라우터 · 조립

**Files:**
- Create: `server/apps/hub/app/ports/input/customer_briefing_use_case.py`
- Create: `server/apps/hub/app/use_cases/customer_briefing_interactor.py`
- Create: `server/apps/hub/adapter/inbound/api/schemas/customer_briefing_schema.py`
- Create: `server/apps/hub/adapter/inbound/api/v1/customer_briefing_router.py`
- Create: `server/apps/hub/dependencies/customer_briefing_provider.py`
- Modify: `server/main.py` (import · `include_router(customer_briefing_router, dependencies=_READERS)` · `_BUILTIN_SPOKES` 에 `"briefing"`)
- Test: `server/apps/hub/tests/app/use_cases/test_customer_briefing_interactor.py`, `server/apps/hub/tests/adapter/test_customer_briefing_router.py`

**Interfaces:**
- Consumes: Task 1 DTO·포트, Task 2 저장소, `RuleBriefingAdapter`
- Produces:
  - `CustomerBriefingUseCase.get(call_id: str) -> CustomerBriefing` (없는 통화 `BriefingCallNotFound`, 빈 ID `ValueError`)
  - `CustomerBriefingInteractor(facts: BriefingFactsPort, composer: CustomerBriefingPort, cache: BriefingCache, now: Callable[[], datetime])`
  - `BriefingCache(max_items: int = 256)` — `async get_or_create(call_id, factory) -> CustomerBriefing`
  - `hub.dependencies.customer_briefing_provider`: `get_briefing_facts_port(request)`, `get_customer_briefing_port() -> CustomerBriefingPort`(기본 `RuleBriefingAdapter()`), `get_customer_briefing_use_case(...)`
  - 라우터 `customer_briefing_router`

- [ ] **Step 1: 실패하는 인터랙터 테스트를 쓴다**

```python
# Requirement: F-3
import asyncio
from datetime import datetime, timezone

import pytest

from hub.app.dtos.customer_briefing_dto import (
    BriefingCallNotFound, BriefingComposition, BriefingFacts, BriefingPurpose, PriorCall,
)
from hub.app.ports.output.briefing_facts_port import BriefingFactsPort
from hub.app.ports.output.customer_briefing_port import CustomerBriefingPort
from hub.app.use_cases.customer_briefing_interactor import BriefingCache, CustomerBriefingInteractor

T = datetime(2026, 10, 6, 5, 0, tzinfo=timezone.utc)
PRIOR = PriorCall(call_id="p1", started_at=T, inquiry_type="일반행정", summary_text="요약", summary_confirmed=True,
                  open_follow_ups=("회신",), call_guard_categories=("insult",))


class _Facts(BriefingFactsPort):
    def __init__(self, facts):
        self.facts = facts

    async def collect(self, call_id):
        return self.facts


class _Composer(CustomerBriefingPort):
    def __init__(self):
        self.calls = 0

    async def compose(self, facts):
        self.calls += 1
        await asyncio.sleep(0.01)
        return BriefingComposition(BriefingPurpose("후속 확인", "확인 전화로 보입니다", "model"), ("줄1",))


def _it(facts, composer=None):
    return CustomerBriefingInteractor(_Facts(facts), composer or _Composer(), BriefingCache(), now=lambda: T)


@pytest.mark.asyncio
async def test_not_found():
    with pytest.raises(BriefingCallNotFound):
        await _it(None).get("x")


@pytest.mark.asyncio
async def test_empty_id_is_value_error():
    with pytest.raises(ValueError):
        await _it(None).get("  ")


@pytest.mark.asyncio
async def test_unidentified_does_not_compose():
    c = _Composer()
    b = await _it(BriefingFacts("now", customer_identified=False), c).get("now")
    assert b.status == "unidentified" and b.purpose is None and c.calls == 0


@pytest.mark.asyncio
async def test_first_contact_does_not_compose():
    c = _Composer()
    b = await _it(BriefingFacts("now", customer_identified=True), c).get("now")
    assert b.status == "first_contact" and b.prior_call_count == 0 and c.calls == 0


@pytest.mark.asyncio
async def test_ready_carries_signals():
    b = await _it(BriefingFacts("now", True, (PRIOR,), blacklisted=True)).get("now")
    assert b.status == "ready" and b.prior_call_count == 1 and b.open_follow_ups == 1
    assert b.call_guard_categories == ("insult",) and b.blacklisted and b.purpose.category == "후속 확인"


@pytest.mark.asyncio
async def test_concurrent_requests_compose_once():
    c = _Composer()
    it = _it(BriefingFacts("now", True, (PRIOR,)), c)
    a, b = await asyncio.gather(it.get("now"), it.get("now"))
    assert c.calls == 1 and a == b
```

- [ ] **Step 2: 실패 확인**

Run: `cd server && ../.venv/bin/python -m pytest apps/hub/tests/app/use_cases/test_customer_briefing_interactor.py -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 유스케이스 인터페이스·인터랙터를 구현한다**

`server/apps/hub/app/ports/input/customer_briefing_use_case.py`:

```python
# Requirement: F-3
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.customer_briefing_dto import CustomerBriefing


class CustomerBriefingUseCase(ABC):
    """통화 수신 전 고객 브리핑(`decisions/220`). 없는 통화면 `BriefingCallNotFound`."""

    @abstractmethod
    async def get(self, call_id: str) -> CustomerBriefing: ...
```

`server/apps/hub/app/use_cases/customer_briefing_interactor.py`:

```python
# Requirement: F-3
"""브리핑 인터랙터 — 사실을 받아 상태를 가르고, 지난 통화가 있을 때만 composer 를 부른다. **목적을 정하지 않는다**(포트 몫).

같은 통화는 한 번만 만든다 — 화면이 `started` 를 다시 받거나 재렌더해도 모델이 두 번 돌지 않게(`BriefingCache`).
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from datetime import datetime
from typing import Awaitable, Callable

from hub.app.dtos.customer_briefing_dto import BriefingCallNotFound, CustomerBriefing
from hub.app.ports.input.customer_briefing_use_case import CustomerBriefingUseCase
from hub.app.ports.output.briefing_facts_port import BriefingFactsPort
from hub.app.ports.output.customer_briefing_port import CustomerBriefingPort


class BriefingCache:
    def __init__(self, max_items: int = 256) -> None:
        self._max = max_items
        self._done: OrderedDict[str, CustomerBriefing] = OrderedDict()
        self._inflight: dict[str, asyncio.Future] = {}

    async def get_or_create(self, call_id: str, factory: Callable[[], Awaitable[CustomerBriefing]]) -> CustomerBriefing:
        if call_id in self._done:
            self._done.move_to_end(call_id)
            return self._done[call_id]
        if call_id in self._inflight:
            return await self._inflight[call_id]
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        self._inflight[call_id] = fut
        try:
            result = await factory()
        except BaseException as exc:
            fut.set_exception(exc)
            fut.exception()  # 기다리는 쪽이 없어도 「처리 안 된 예외」 경고가 나지 않게
            raise
        finally:
            self._inflight.pop(call_id, None)
        fut.set_result(result)
        self._done[call_id] = result
        if len(self._done) > self._max:
            self._done.popitem(last=False)
        return result


class CustomerBriefingInteractor(CustomerBriefingUseCase):
    def __init__(self, facts: BriefingFactsPort, composer: CustomerBriefingPort, cache: BriefingCache,
                 now: Callable[[], datetime]) -> None:
        self._facts = facts
        self._composer = composer
        self._cache = cache
        self._now = now

    async def get(self, call_id: str) -> CustomerBriefing:
        if not call_id.strip():
            raise ValueError("call_id 가 비어 있습니다")
        return await self._cache.get_or_create(call_id, lambda: self._build(call_id))

    async def _build(self, call_id: str) -> CustomerBriefing:
        facts = await self._facts.collect(call_id)
        if facts is None:
            raise BriefingCallNotFound(f"통화가 없습니다: {call_id}")
        prior = facts.prior_calls
        common = dict(call_id=call_id, prior_call_count=len(prior), evidence=prior,
                      open_follow_ups=sum(len(p.open_follow_ups) for p in prior),
                      call_guard_categories=tuple(sorted({c for p in prior for c in p.call_guard_categories})),
                      blacklisted=facts.blacklisted, generated_at=self._now())
        if not facts.customer_identified:
            return CustomerBriefing(status="unidentified", purpose=None, lines=(), **common)
        if not prior:
            return CustomerBriefing(status="first_contact", purpose=None, lines=(), **common)
        comp = await self._composer.compose(facts)
        return CustomerBriefing(status="ready", purpose=comp.purpose, lines=comp.lines, **common)
```

⚠ `BriefingCallNotFound` 는 캐시하지 않는다 — 위 `get_or_create` 는 예외면 `_done` 에 넣지 않는다(이미 그렇다). 미디에이터가 `POST /hub/calls` 직전에 화면이 부르면 404 였다가 곧 생기기 때문이다.

- [ ] **Step 4: 인터랙터 테스트 통과 확인**

Run: `cd server && ../.venv/bin/python -m pytest apps/hub/tests/app/use_cases/test_customer_briefing_interactor.py -q`
Expected: 6 passed

- [ ] **Step 5: 실패하는 라우터 테스트를 쓴다** — `server/apps/hub/tests/adapter/test_customer_briefing_router.py`. `test_call_record_router.py` 의 `app.dependency_overrides` · `TestClient` 방식을 그대로 따른다.

```python
# Requirement: F-3, QUA-1
"""HTTP 표면: 404 · 값은 전부 문자열 · 고객 식별 정보가 응답 어디에도 없다."""

import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from hub.app.dtos.customer_briefing_dto import BriefingFacts, PriorCall
from hub.app.ports.output.briefing_facts_port import BriefingFactsPort
from hub.dependencies.customer_briefing_provider import get_briefing_facts_port, reset_briefing_cache
from main import app

T = datetime(2026, 10, 5, 5, 2, tzinfo=timezone.utc)
PRIOR = PriorCall(call_id="p1", started_at=T, inquiry_type="일반행정", summary_text="위임 등본 문의", summary_confirmed=True,
                  incomplete_procedures=("DASAN-TERM-4.1",))


class _Facts(BriefingFactsPort):
    def __init__(self, facts):
        self.facts = facts

    async def collect(self, call_id):
        return self.facts


def _get(facts, call_id="now"):
    reset_briefing_cache()
    app.dependency_overrides[get_briefing_facts_port] = lambda: _Facts(facts)
    try:
        return TestClient(app).get(f"/hub/calls/{call_id}/briefing")
    finally:
        app.dependency_overrides.pop(get_briefing_facts_port, None)


def test_unknown_call_404():
    assert _get(None).status_code == 404


def test_ready_shape_is_all_strings():
    r = _get(BriefingFacts("now", True, (PRIOR,), blacklisted=False))
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready" and body["prior_call_count"] == "1"
    assert body["purpose"]["category"] == "서류 보완" and body["purpose"]["source"] == "rule"
    assert body["signals"]["blacklisted"] == "false" and body["signals"]["open_follow_ups"] == "0"
    assert body["evidence"][0]["summary_confirmed"] == "true"
    assert body["evidence"][0]["incomplete_procedures"] == ["DASAN-TERM-4.1"]
    assert 1 <= len(body["briefing_lines"]) <= 3


def test_first_contact_has_null_purpose():
    body = _get(BriefingFacts("now", True)).json()
    assert body["status"] == "first_contact" and body["purpose"] is None and body["briefing_lines"] == []


def test_response_has_no_customer_identity():
    text = json.dumps(_get(BriefingFacts("now", True, (PRIOR,))).json(), ensure_ascii=False)
    for key in ("customer_id", "customer_ref", "display_hint", "caller_phone", "hmac"):
        assert key not in text
```

- [ ] **Step 6: 스키마·라우터·프로바이더를 구현한다**

`server/apps/hub/adapter/inbound/api/schemas/customer_briefing_schema.py`:

```python
# Requirement: F-3
"""HTTP 표면 스키마 — 통화 수신 전 고객 브리핑. 값은 전부 문자열(`_types.StrField`, 7.3절 규칙). **고객 식별 정보 필드가 없다.**"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ._types import StrField


class BriefingPurposeSchema(BaseModel):
    category: str = Field(description="재문의 | 후속 확인 | 서류 보완 | 컴플레인 | 신규 문의 — **추정**이다")
    text: str
    source: str = Field(description="model | rule")


class BriefingEvidenceSchema(BaseModel):
    call_id: str
    started_at: str
    inquiry_type: str | None = None
    summary_confirmed: StrField
    incomplete_procedures: list[str]


class BriefingSignalsSchema(BaseModel):
    open_follow_ups: StrField
    call_guard_categories: list[str]
    blacklisted: StrField


class CustomerBriefingResponse(BaseModel):
    call_id: str
    status: str = Field(description="ready | first_contact | unidentified")
    prior_call_count: StrField
    purpose: BriefingPurposeSchema | None = None
    briefing_lines: list[str]
    evidence: list[BriefingEvidenceSchema]
    signals: BriefingSignalsSchema
    generated_at: str
```

`server/apps/hub/adapter/inbound/api/v1/customer_briefing_router.py`:

```python
# Requirement: F-3
"""GET /hub/calls/{call_id}/briefing — 「통화받기」 전 고객 브리핑(`decisions/220`). 목적은 **추정**이다."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from hub.adapter.inbound.api.schemas.customer_briefing_schema import (
    BriefingEvidenceSchema, BriefingPurposeSchema, BriefingSignalsSchema, CustomerBriefingResponse,
)
from hub.app.dtos.customer_briefing_dto import BriefingCallNotFound
from hub.app.ports.input.customer_briefing_use_case import CustomerBriefingUseCase
from hub.dependencies.customer_briefing_provider import get_customer_briefing_use_case

customer_briefing_router = APIRouter(prefix="/hub", tags=["hub"])


@customer_briefing_router.get("/calls/{call_id}/briefing", response_model=CustomerBriefingResponse)
async def get_customer_briefing(
    call_id: str,
    use_case: CustomerBriefingUseCase = Depends(get_customer_briefing_use_case),
) -> CustomerBriefingResponse:
    try:
        b = await use_case.get(call_id)
    except BriefingCallNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return CustomerBriefingResponse(
        call_id=b.call_id,
        status=b.status,
        prior_call_count=b.prior_call_count,
        purpose=None if b.purpose is None else BriefingPurposeSchema(
            category=b.purpose.category, text=b.purpose.text, source=b.purpose.source),
        briefing_lines=list(b.lines),
        evidence=[BriefingEvidenceSchema(call_id=p.call_id, started_at=p.started_at.isoformat(),
                                         inquiry_type=p.inquiry_type, summary_confirmed=p.summary_confirmed,
                                         incomplete_procedures=list(p.incomplete_procedures))
                  for p in b.evidence],
        signals=BriefingSignalsSchema(open_follow_ups=b.open_follow_ups,
                                      call_guard_categories=list(b.call_guard_categories),
                                      blacklisted=b.blacklisted),
        generated_at=b.generated_at.isoformat(),
    )
```

`server/apps/hub/dependencies/customer_briefing_provider.py`:

```python
# Requirement: F-3, SEC-2
"""브리핑 조립. 기본 composer 는 **규칙 브리핑**(`server/apps/briefing`) — 모델은 `server/main.py` 의
`_wire_briefing_model` 이 `get_customer_briefing_port` 를 덮어써 얹는다. PostgreSQL 이 없으면 501."""

from __future__ import annotations

from datetime import datetime, timezone

from briefing.adapter.outbound.rule_briefing_adapter import RuleBriefingAdapter
from fastapi import Depends, HTTPException, Request, status

from hub.adapter.outbound.postgres.briefing_facts_repository import PostgresBriefingFactsRepository
from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.app.ports.input.customer_briefing_use_case import CustomerBriefingUseCase
from hub.app.ports.output.briefing_facts_port import BriefingFactsPort
from hub.app.ports.output.customer_briefing_port import CustomerBriefingPort
from hub.app.use_cases.customer_briefing_interactor import BriefingCache, CustomerBriefingInteractor

_CACHE = BriefingCache()


def reset_briefing_cache() -> None:
    """테스트 전용 — 프로세스 단일 캐시를 비운다."""
    global _CACHE
    _CACHE = BriefingCache()


def get_briefing_facts_port(request: Request) -> BriefingFactsPort:
    settings = request.app.state.settings
    if not settings.postgres_configured:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED,
                            detail="PostgreSQL 이 설정되지 않았습니다 — infra/README.md 참고")
    return PostgresBriefingFactsRepository(build_connection_factory(settings))


def get_customer_briefing_port() -> CustomerBriefingPort:
    return RuleBriefingAdapter()


def get_customer_briefing_use_case(
    facts: BriefingFactsPort = Depends(get_briefing_facts_port),
    composer: CustomerBriefingPort = Depends(get_customer_briefing_port),
) -> CustomerBriefingUseCase:
    return CustomerBriefingInteractor(facts=facts, composer=composer, cache=_CACHE,
                                      now=lambda: datetime.now(timezone.utc))
```

`server/main.py`:
- 라우터 import 블록(알파벳 순 자리)에 `from hub.adapter.inbound.api.v1.customer_briefing_router import customer_briefing_router  # noqa: E402`
- 등록부에 `app.include_router(customer_briefing_router, dependencies=_READERS)` (`call_record_router` 다음 줄)
- `_BUILTIN_SPOKES = ("masking", "closure_gate", "postcall", "briefing")`

- [ ] **Step 7: 전체 서버 테스트·계약**

Run: `cd server && ../.venv/bin/python -m pytest -q && PYTHONPATH=apps ../.venv/bin/lint-imports --config .importlinter`
Expected: 기존 1,452 + 새 테스트 전부 통과(스포크 목록을 고정한 테스트가 깨지면 `"briefing"` 을 기대값에 더한다) · `Contracts: 5 kept, 0 broken.`

- [ ] **Step 8: 커밋**

```bash
git add server/apps/hub server/main.py
git commit -m "code(f3): GET /hub/calls/{id}/briefing — 상태 분기·캐시·동시 요청 합치기, 규칙 브리핑이 기본 (decisions/220)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: 모델 어댑터(`ai/`) · 조립

**Files:**
- Create: `ai/apps/customer_briefing/__init__.py` · `domain/__init__.py` · `domain/services/__init__.py` · `adapter/__init__.py` · `adapter/outbound/__init__.py` · `tests/__init__.py` · `tests/domain/__init__.py` · `tests/adapter/__init__.py`
- Create: `ai/apps/customer_briefing/domain/services/briefing_checks.py`
- Create: `ai/apps/customer_briefing/adapter/outbound/model_briefing_adapter.py`
- Modify: `ai/provider.py` (`build_briefing_provider`)
- Modify: `ai/.importlinter` (`customer_briefing` 를 root_packages · 계약 1 containers · 계약 2 modules · 계약 3 `customer_briefing.domain`)
- Modify: `server/main.py` (`_wire_briefing_model` + 호출 · 스포크 `briefing_model`)
- Test: `ai/apps/customer_briefing/tests/domain/test_briefing_checks.py`, `ai/apps/customer_briefing/tests/adapter/test_model_briefing_adapter.py`

**Interfaces:**
- Consumes: `CustomerBriefingPort`, `BriefingFacts`, `BriefingComposition`, `BriefingPurpose`, `BRIEFING_PURPOSES` (hub) · `facts_text` 는 **import 하지 않는다**(server 스포크 — ai 는 hub 만 안다) → 같은 일을 하는 `render_facts` 를 ai 도메인에 둔다
- Produces:
  - `customer_briefing.domain.services.briefing_checks`: `render_facts(facts) -> str`, `build_messages(facts) -> list[dict]`, `OUTPUT_SCHEMA: dict`, `briefing_problems(category: str, purpose: str, lines: list[str], source_text: str) -> list[str]`
  - `customer_briefing.adapter.outbound.model_briefing_adapter.ModelBriefingAdapter(fallback: CustomerBriefingPort, *, chat, timeout_s: float = 10.0)`
  - `provider.build_briefing_provider(fallback, *, ollama_url, model) -> Callable[[], CustomerBriefingPort]`

- [ ] **Step 1: 실패하는 검사 테스트**

```python
# Requirement: F-3
from datetime import datetime, timezone

from customer_briefing.domain.services.briefing_checks import briefing_problems, build_messages, render_facts
from hub.app.dtos.customer_briefing_dto import BriefingFacts, PriorCall

T = datetime(2026, 10, 5, 5, 2, tzinfo=timezone.utc)
FACTS = BriefingFacts("now", True, (PriorCall(call_id="p1", started_at=T, inquiry_type="상하수도",
                                              summary_text="단수 3일째 처리 지연 문의", summary_confirmed=True,
                                              open_follow_ups=("담당 부서 회신",)),))


def test_render_has_no_ids():
    text = render_facts(FACTS)
    assert "p1" not in text and "단수 3일째" in text and "10-05" in text


def test_clean_output_passes():
    assert briefing_problems("컴플레인", "회신이 없어 다시 건 것으로 보입니다", ["지난 통화 10-05 상하수도"], render_facts(FACTS)) == []


def test_out_of_list_category():
    assert "목록 밖 범주 서류보완" in briefing_problems("서류보완", "x", ["a"], render_facts(FACTS))


def test_invented_digit():
    probs = briefing_problems("컴플레인", "5일째 지연", ["a"], render_facts(FACTS))
    assert any("재료에 없는 숫자 5" in p for p in probs)


def test_masked_digits_do_not_count():
    assert briefing_problems("재문의", "번호 ****로 문의", ["a"], "번호 **** 문의") == []


def test_forbidden_and_shape():
    assert any("금지 표현" in p for p in briefing_problems("컴플레인", "위험 고객입니다", ["a"], ""))
    assert any("줄 수" in p for p in briefing_problems("재문의", "x", [], ""))
    assert any("줄 수" in p for p in briefing_problems("재문의", "x", ["a", "b", "c", "d"], ""))


def test_messages_list_categories():
    msgs = build_messages(FACTS)
    assert "후속 확인" in msgs[0]["content"] and "단수 3일째" in msgs[1]["content"]
```

- [ ] **Step 2: 실패 확인**

Run: `cd ai && ../.venv/bin/python -m pytest apps/customer_briefing/tests/domain -q`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 검사·프롬프트 구현** — `ai/apps/customer_briefing/domain/services/briefing_checks.py`

```python
# Requirement: F-3
"""모델 브리핑의 프롬프트와 **출력 검사** — 순수 파이썬(`ai/.importlinter` 계약 3). 판정은 하지 않는다(`decisions/220` 2절).

검사에 하나라도 걸리면 규칙 브리핑으로 내려간다(어댑터 몫).
"""

from __future__ import annotations

import re
from datetime import timedelta, timezone

from hub.app.dtos.customer_briefing_dto import BRIEFING_PURPOSES, BriefingFacts

_KST = timezone(timedelta(hours=9))
FORBIDDEN_TERMS = ("안전합니다", "위험", "등급", "점수", "%", "확실", "무조건", "보장", "틀림없", "요주의")
PURPOSE_MAX_CHARS = 120
LINE_MAX_CHARS = 90
_DIGITS = re.compile(r"\d+")

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": list(BRIEFING_PURPOSES)},
        "purpose": {"type": "string"},
        "lines": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 3},
    },
    "required": ["category", "purpose", "lines"],
}

SYSTEM_PROMPT = (
    "상담원이 전화를 받기 전에 읽을 고객 브리핑을 쓴다. 아래 '지난 통화 사실'만 근거로 쓰고 없는 사실·숫자·이름을 만들지 않는다. "
    "이번 통화의 목적을 다음 중 하나로 추정한다: " + ", ".join(BRIEFING_PURPOSES) + ". "
    "purpose 는 '~로 보입니다'로 끝나는 한 문장, lines 는 상담원이 3초 안에 읽을 짧은 줄 세 개 이하다. "
    "평가·점수·단정(위험, 요주의 등)을 쓰지 않는다. *로 가려진 부분은 추측하지 않는다."
)


def render_facts(facts: BriefingFacts) -> str:
    out = []
    for i, c in enumerate(facts.prior_calls, start=1):
        day = c.started_at.astimezone(_KST).strftime("%m-%d")
        out.append(f"[지난 통화 {i}] {day} · 유형 {c.inquiry_type or '미정'} · 요약 {c.summary_text or '없음'}")
        if c.open_follow_ups:
            out.append("  후속조치: " + "; ".join(c.open_follow_ups))
        if c.incomplete_procedures:
            out.append("  서류 안내 미완료 절차: " + ", ".join(c.incomplete_procedures))
        if c.call_guard_categories:
            out.append("  고객 쪽 신호: " + ", ".join(c.call_guard_categories))
    if facts.blacklisted:
        out.append("블랙리스트 적용 중")
    return "\n".join(out)


def build_messages(facts: BriefingFacts) -> list[dict[str, str]]:
    return [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "지난 통화 사실:\n" + render_facts(facts)}]


def briefing_problems(category: str, purpose: str, lines: list[str], source_text: str) -> list[str]:
    problems: list[str] = []
    if category not in BRIEFING_PURPOSES:
        problems.append(f"목록 밖 범주 {category}")
    if not purpose.strip():
        problems.append("빈 목적")
    if len(purpose) > PURPOSE_MAX_CHARS:
        problems.append(f"목적 길이 {len(purpose)}자")
    if not 1 <= len(lines) <= 3:
        problems.append(f"줄 수 {len(lines)}")
    for line in lines:
        if len(line) > LINE_MAX_CHARS:
            problems.append(f"줄 길이 {len(line)}자")
    src_digits = set(_DIGITS.findall(source_text))
    for d in _DIGITS.findall(" ".join([purpose, *lines])):
        if d not in src_digits:
            problems.append(f"재료에 없는 숫자 {d}")
    joined = " ".join([purpose, *lines])
    for term in FORBIDDEN_TERMS:
        if term in joined:
            problems.append(f"금지 표현 {term}")
    return problems
```

- [ ] **Step 4: 실패하는 어댑터 테스트**

```python
# Requirement: F-3
import json
import time
from datetime import datetime, timezone

import pytest

from customer_briefing.adapter.outbound.model_briefing_adapter import ModelBriefingAdapter
from hub.app.dtos.customer_briefing_dto import (
    BriefingComposition, BriefingFacts, BriefingPurpose, PriorCall,
)
from hub.app.ports.output.customer_briefing_port import CustomerBriefingPort

T = datetime(2026, 10, 5, 5, 2, tzinfo=timezone.utc)
FACTS = BriefingFacts("now", True, (PriorCall(call_id="p1", started_at=T, inquiry_type="상하수도",
                                              summary_text="단수 처리 지연 문의", summary_confirmed=True,
                                              open_follow_ups=("담당 부서 회신",)),))
RULE = BriefingComposition(BriefingPurpose("후속 확인", "규칙 문장", "rule"), ("규칙 줄",))


class _Rule(CustomerBriefingPort):
    async def compose(self, facts):
        return RULE


class _Chat:
    model = "m"

    def __init__(self, payload=None, fail=False, delay=0.0):
        self.payload, self.fail, self.delay, self.calls = payload, fail, delay, 0

    def chat(self, messages, *, schema=None):
        self.calls += 1
        time.sleep(self.delay)
        if self.fail:
            raise OSError("down")

        class R:  # ChatResult 와 같은 모양
            content = json.dumps(self.payload, ensure_ascii=False)
        return R()


def _good(**over):
    p = {"category": "컴플레인", "purpose": "회신이 없어 다시 건 것으로 보입니다", "lines": ["지난 통화 10-05 상하수도"]}
    p.update(over)
    return p


@pytest.mark.asyncio
async def test_model_output_used_when_clean():
    c = await ModelBriefingAdapter(_Rule(), chat=_Chat(_good())).compose(FACTS)
    assert c.purpose.source == "model" and c.purpose.category == "컴플레인"


@pytest.mark.asyncio
async def test_out_of_list_category_falls_back():
    assert (await ModelBriefingAdapter(_Rule(), chat=_Chat(_good(category="서류보완"))).compose(FACTS)) == RULE


@pytest.mark.asyncio
async def test_invented_digit_falls_back():
    assert (await ModelBriefingAdapter(_Rule(), chat=_Chat(_good(purpose="7일째 지연으로 보입니다"))).compose(FACTS)) == RULE


@pytest.mark.asyncio
async def test_broken_json_and_errors_fall_back():
    class Bad(_Chat):
        def chat(self, messages, *, schema=None):
            class R:
                content = "그냥 문장"
            return R()
    assert (await ModelBriefingAdapter(_Rule(), chat=Bad()).compose(FACTS)) == RULE
    assert (await ModelBriefingAdapter(_Rule(), chat=_Chat(fail=True)).compose(FACTS)) == RULE


@pytest.mark.asyncio
async def test_timeout_falls_back():
    a = ModelBriefingAdapter(_Rule(), chat=_Chat(_good(), delay=0.3), timeout_s=0.05)
    assert (await a.compose(FACTS)) == RULE


@pytest.mark.asyncio
async def test_no_chat_is_rule():
    assert (await ModelBriefingAdapter(_Rule(), chat=None).compose(FACTS)) == RULE
```

- [ ] **Step 5: 어댑터 구현** — `ai/apps/customer_briefing/adapter/outbound/model_briefing_adapter.py`

```python
# Requirement: F-3
"""`CustomerBriefingPort` 모델 구현 — 규칙 브리핑 **위에** 목적 범주·세 줄을 얹는다(`decisions/220` 2절).

모델 실패 · 시간 초과(기본 10초) · JSON 아님 · 검사(`briefing_problems`) 하나라도 걸림 → **규칙 브리핑 그대로**.
`fallback`·`chat` 은 주입이다 — `server/apps/briefing`·`ai/apps/generation` 을 import 하지 않는다(계약 2).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Protocol

from hub.app.dtos.customer_briefing_dto import BriefingComposition, BriefingFacts, BriefingPurpose
from hub.app.ports.output.customer_briefing_port import CustomerBriefingPort

from ...domain.services.briefing_checks import OUTPUT_SCHEMA, briefing_problems, build_messages, render_facts

log = logging.getLogger(__name__)


class ChatClient(Protocol):
    model: str

    def chat(self, messages: list[dict[str, str]], *, schema: dict | None = None): ...


class ModelBriefingAdapter(CustomerBriefingPort):
    def __init__(self, fallback: CustomerBriefingPort, *, chat: ChatClient | None, timeout_s: float = 10.0) -> None:
        self._fallback = fallback
        self._chat = chat
        self._timeout = timeout_s

    async def compose(self, facts: BriefingFacts) -> BriefingComposition:
        rule = await self._fallback.compose(facts)
        if self._chat is None:
            return rule
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(self._chat.chat, build_messages(facts), schema=OUTPUT_SCHEMA), timeout=self._timeout)
            data = json.loads(result.content)
            category, purpose, lines = str(data["category"]), str(data["purpose"]), [str(x) for x in data["lines"]]
        except Exception as e:  # noqa: BLE001 — 어떤 실패든 규칙 브리핑으로
            log.warning("브리핑 모델 실패 → 규칙: %s", type(e).__name__)
            return rule
        problems = briefing_problems(category, purpose, lines, render_facts(facts))
        if problems:
            log.info("브리핑 모델 출력 검사 걸림 → 규칙: %s", problems)
            return rule
        return BriefingComposition(purpose=BriefingPurpose(category, purpose, "model"), lines=tuple(lines))
```

⚠ `asyncio.wait_for` 는 스레드를 죽이지 못한다 — 시간을 넘긴 `chat` 은 뒤에서 끝까지 돈다. `OllamaChat` 자체 `timeout_s` 도 같은 값(10초)으로 주어 묶는다(Step 6).

- [ ] **Step 6: 조립** — `ai/provider.py` 에 `build_postcall_provider` 다음 자리:

```python
def build_briefing_provider(
    fallback: CustomerBriefingPort,
    *,
    ollama_url: str | None,
    model: str | None,
) -> Callable[[], CustomerBriefingPort]:
    """`get_customer_briefing_port` 를 대체할 프로바이더(F-3, `decisions/220`). `fallback` 은 서버 규칙 브리핑 — 합성 루트가 넘긴다."""
    from customer_briefing.adapter.outbound.model_briefing_adapter import ModelBriefingAdapter

    chat = None
    if ollama_url and model:
        from generation.adapter.outbound.ollama_chat import OllamaChat

        chat = OllamaChat(ollama_url, model=model, num_predict=200, timeout_s=10)
    port = ModelBriefingAdapter(fallback, chat=chat, timeout_s=10.0)
    return lambda: port
```

`ai/provider.py` 맨 위 import 에 `from hub.app.ports.output.customer_briefing_port import CustomerBriefingPort` 를 다른 포트 import 와 같은 자리에 더한다.

`server/main.py` — `_wire_postcall_model` 다음에:

```python
def _wire_briefing_model(app: FastAPI, settings: Settings) -> str | None:
    """F-3 통화 수신 전 브리핑의 모델 겹(`decisions/220`). 요약과 **같은 조건**이다 — 새 키 없음.
    안 켜면 규칙 브리핑(`server/apps/briefing`)이 그대로 나간다."""
    model = settings.postcall_model or settings.generation_model
    if not (settings.ollama_url and model):
        return None
    sys.path.insert(0, str(AI_APPS))
    sys.path.insert(0, str(AI_APPS.parent))
    try:
        from provider import build_briefing_provider  # noqa: PLC0415
    except (ModuleNotFoundError, ImportError):
        return None

    from briefing.adapter.outbound.rule_briefing_adapter import RuleBriefingAdapter  # noqa: PLC0415
    from hub.dependencies.customer_briefing_provider import get_customer_briefing_port  # noqa: PLC0415

    app.dependency_overrides.setdefault(
        get_customer_briefing_port,
        build_briefing_provider(RuleBriefingAdapter(), ollama_url=settings.ollama_url, model=model),
    )
    return "briefing_model"
```

`_wire_postcall_model` 을 부르는 lifespan 자리(그 결과를 `SPOKES` 에 더하는 곳)를 찾아 **같은 방식으로** `_wire_briefing_model` 을 부르고 이름을 더한다.

- [ ] **Step 7: ai 계약 등록 · 전체 확인**

`ai/.importlinter`: `root_packages` · 계약 1 `containers` · 계약 2 `modules` 에 `customer_briefing`, 계약 3 `source_modules` 에 `customer_briefing.domain`. 머리말에 `customer_briefing(F-3 브리핑 모델 겹)은 2026-10-06 — server/apps/briefing(규칙) 위에 얹는다` 한 줄.

Run: `cd ai && ../.venv/bin/python -m pytest -q && PYTHONPATH=apps:../server/apps ../.venv/bin/lint-imports --config .importlinter`
Expected: 기존 581 + 새 13 통과 · `Contracts: 3 kept, 0 broken.`
Run: `cd server && ../.venv/bin/python -m pytest -q && PYTHONPATH=apps ../.venv/bin/lint-imports --config .importlinter`
Expected: 전부 통과 · `5 kept`

- [ ] **Step 8: 커밋**

```bash
git add ai/apps/customer_briefing ai/provider.py ai/.importlinter server/main.py
git commit -m "code(f3): 브리핑 모델 겹 — 목적 범주·세 줄, 검사 걸리면 규칙 (decisions/220)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: 재생기 `--ring-seconds`

**Files:**
- Modify: `services/call-mediator/scripts/replay_persona_call.ts` (`Args` 타입 · `parseArgs` · `main` · 머리말 사용법)
- Test: `services/call-mediator/test/replay_args.test.ts` (생성) — `parseArgs` 가 export 돼 있지 않으면 `export` 를 붙인다(동작 변화 없음)

**Interfaces:**
- Produces: CLI 플래그 `--ring-seconds <초>` — 통화 채널을 연 뒤(=`started` 방송) 그 초만큼 첫 발화를 미룬다. 기본 0(지금과 같음)

- [ ] **Step 1: 실패하는 테스트**

```ts
// Requirement: F-3
import { test } from "node:test";
import assert from "node:assert/strict";
import { parseArgs } from "../scripts/replay_persona_call.ts";

test("--ring-seconds 기본은 0 — 지금 동작 그대로", () => {
  assert.equal(parseArgs(["SYN-004"]).ringMs, 0);
});

test("--ring-seconds 12 → 12000ms", () => {
  assert.equal(parseArgs(["SYN-004", "--ring-seconds", "12"]).ringMs, 12_000);
});

test("--ring-seconds 음수·숫자 아님은 거절", () => {
  assert.throws(() => parseArgs(["SYN-004", "--ring-seconds", "-1"]));
  assert.throws(() => parseArgs(["SYN-004", "--ring-seconds", "abc"]));
});
```

⚠ 스크립트를 import 하면 맨 아래 `main()` 이 돌 수 있다 — 파일 끝의 실행부가 `import.meta.url === pathToFileURL(process.argv[1]).href` 같은 진입 확인으로 감싸져 있는지 먼저 본다. 없으면 그 확인을 넣는다(`node scripts/replay_persona_call.ts …` 로 직접 실행할 때만 `main()`).

- [ ] **Step 2: 실패 확인**

Run: `cd services/call-mediator && node --experimental-strip-types --test test/replay_args.test.ts`
Expected: FAIL — `ringMs` 가 undefined 이거나 export 없음

- [ ] **Step 3: 구현**
- `interface Args` 에 `ringMs: number;`
- `parseArgs` 기본값에 `ringMs: 0,` · 분기 추가:

```ts
    } else if (flag === "--ring-seconds") {
      args.ringMs = Number(value) * 1000;
      i += 1;
```

- 검증부에 `if (!Number.isFinite(args.ringMs) || args.ringMs < 0) { throw new Error("--ring-seconds 는 0 이상의 초다"); }`
- `main` 에서 `const sockets = … await openSpeakers(…)` 바로 다음, 턴 루프 전에:

```ts
  if (args.ringMs > 0 && !args.dryRun) {
    // 벨이 울리는 시간 — 통화는 이미 열려 `started` 가 나갔다. 그동안 화면이 고객 브리핑(F-3, decisions/220)을 받는다
    console.log(`  ☎ 벨 ${args.ringMs / 1000}초 — 첫 발화를 미룬다`);
    await sleep(args.ringMs);
  }
```

- 머리말 사용법 줄에 `[--ring-seconds 15]` 와 한 줄 설명 추가.

- [ ] **Step 4: 통과·회귀 확인**

Run: `cd services/call-mediator && node --experimental-strip-types --test test/replay_args.test.ts && npm run typecheck && npm test 2>&1 | grep -E "^ℹ (pass|fail)"`
Expected: 3 pass · typecheck 무오류 · 기존 184 + 3 pass, fail 0

- [ ] **Step 5: 커밋**

```bash
git add services/call-mediator/scripts/replay_persona_call.ts services/call-mediator/test/replay_args.test.ts
git commit -m "code(f3): 재생기 --ring-seconds — 벨 시간 동안 첫 발화를 미룬다 (decisions/220)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

⚠ 이 파일은 `services/call-mediator/scripts/` 라 **배포 이미지 경로가 아니다** — `scripts/check_release_tags.py` 의 call-mediator 정규식(`src/`·`package*.json`)에 걸리지 않는지 `python3 scripts/check_release_tags.py` 로 확인한다. `test/` 는 걸릴 수 있다 — 걸리면 태그 문제는 PR 단계에서 따로 다룬다(이 계획은 PR 을 열지 않는다).

---

### Task 6: 대본 고객 셋 · 채점 스크립트

**Files:**
- Create: `scripts/persona_sim/dasan-briefing/SYN-301.json` … `SYN-306.json`
- Create: `scripts/persona_sim/dasan-briefing/README.md`
- Create: `scripts/persona_sim/briefing_check.py`
- Test: `scripts/persona_sim/tests/test_briefing_check.py`

**Interfaces:**
- Consumes: 재생기 `--ring-seconds` · `--call-id` · `--close --core-url`(Task 5 · 기존) · `GET /hub/calls/{id}/briefing`(Task 3)
- Produces: `briefing_check.py` 의 순수 함수 `score(results: list[dict]) -> dict` (`{"n": int, "match": int, "by_source": {"model": int, "rule": int}, "unstable": list[str]}`)

- [ ] **Step 1: 대본 형식을 익힌다** — `scripts/persona_sim/dasan-v0/SYN-004.json`·`SYN-006.json`·`SYN-007.json` 과 `scripts/persona_sim/README.md` 를 읽는다. 필드(`id`·`version`·`source`·`generated_by`·`title`·`length_class`·`turn_count`·`caller_number`·`agent_persona`·`customer_persona`·`procedure`·`turns[seq,speaker,text,tone,labels]`·`expected`·`notes`)를 그대로 쓴다. 절차 조항 ID 와 그 조항의 필요서류는 `knowledge-base/dasan/terms/TERM.md` 와 `server/apps/closure_gate/domain/value_objects/closure_rule.py` 에서 **실제로 규칙이 있는 조항**을 고른다(규칙이 없으면 필요서류 판정이 안 생겨 「서류 보완」 재료가 없다).

- [ ] **Step 2: 대본 여섯 개를 쓴다** — `version: "dasan-briefing"`, `source: "synthetic"`, `generated_by: "Claude Code (claude-opus-5-5) · 2026-10-06 · 사람 검토 전"`. **폭언·성적 표현 금지**(`209`). 개인정보는 실존 불가 가짜 값.

| ID | 고객 · 번호 | 역할 | 내용 | `expected.briefing` |
|---|---|---|---|---|
| SYN-301 | A · `01000000301` | 지난 통화 | 가족 대신 서류 발급(규칙 있는 대리 발급 조항) — 상담원이 필요서류 중 **하나를 안내하지 않고** 끝낸다(필요서류 판정 `incomplete` 가 남게) | `{"role": "prior", "for": "SYN-302"}` |
| SYN-302 | A · 같은 번호 | 이번 통화 | 「지난번에 안내받고 갔는데 서류 하나가 없다고 돌려보내졌어요」 | `{"role": "current", "purpose_category": "서류 보완", "prior": ["SYN-301"]}` |
| SYN-303 | B · `01000000302` | 지난 통화 | 단수(상하수도 조항) 처리 지연 불만 — 고객 톤 `raised`(욕설 없음), 상담원 「담당 부서에서 오늘 중 회신드리겠습니다」(후속조치) | `{"role": "prior", "for": "SYN-304"}` |
| SYN-304 | B · 같은 번호 | 이번 통화 | 「그때 연락 준다더니 이틀째 아무 연락이 없어요」 | `{"role": "current", "purpose_category": "컴플레인", "prior": ["SYN-303"]}` |
| SYN-305 | C · `01000000303` | 지난 통화 | 외국인 고객(서툰 한국어) 여권 재발급(`DASAN-TERM-4.23`) — 상담원 「접수되면 문자로 결과 안내드리겠습니다」(후속조치) | `{"role": "prior", "for": "SYN-306"}` |
| SYN-306 | C · 같은 번호 | 이번 통화 | 「저번에 여권 신청했는데요, 어떻게 됐어요」 | `{"role": "current", "purpose_category": "후속 확인", "prior": ["SYN-305"]}` |

**정답 목적(`purpose_category`)은 브리핑을 한 번도 돌리기 전에 적는다** — 커밋으로 그 순서를 남긴다(Step 6 의 커밋이 채점 코드보다 먼저다). 각 「이번 통화」의 첫 고객 발화가 목적을 드러내지만, **브리핑은 그 발화를 보지 못한다**(벨 시간에 만든다) — 지난 통화 사실만으로 맞혀야 한다는 점을 `notes` 에 적는다.

`README.md`: 묶음의 목적(`decisions/220`) · 고객 셋 표 · 「정답 라벨은 대본 작성자가 쓴 상한」 · 돌리는 법(Step 5 명령).

- [ ] **Step 3: 실패하는 채점 테스트**

```python
# Requirement: F-3, E-1
from briefing_check import score


def _r(sid, cat, source="model", run=1, expected="서류 보완"):
    return {"script": sid, "run": run, "expected": expected, "category": cat, "source": source}


def test_score_counts_matches_and_sources():
    s = score([_r("SYN-302", "서류 보완"), _r("SYN-304", "후속 확인", "rule", expected="컴플레인")])
    assert s["n"] == 2 and s["match"] == 1 and s["by_source"] == {"model": 1, "rule": 1}


def test_unstable_when_category_changes_across_runs():
    s = score([_r("SYN-302", "서류 보완", run=1), _r("SYN-302", "재문의", run=2)])
    assert s["unstable"] == ["SYN-302"]


def test_missing_category_is_a_miss_not_an_error():
    s = score([_r("SYN-302", None)])
    assert s["n"] == 1 and s["match"] == 0
```

`scripts/persona_sim/tests/` 가 `briefing_check` 를 import 할 수 있게, 같은 폴더의 기존 테스트가 경로를 어떻게 잡는지(`conftest.py` 또는 `sys.path`) 확인하고 따른다.

- [ ] **Step 4: 채점 스크립트 구현** — `scripts/persona_sim/briefing_check.py`

```python
# Requirement: F-3, E-1
"""F-3 통화 수신 전 브리핑 왕복 검사 (`decisions/220` 6절).

고객마다: 지난 통화를 실제 파이프라인으로 재생(--close 로 요약까지) → 이번 통화를 --ring-seconds 로 재생하며
벨 시간 안에 GET /hub/calls/{id}/briefing 을 부른다 → 범주를 대본 라벨과 글자 비교(규칙 채점, 절대 원칙 1).

⚠ source: synthetic — 라벨은 대본 작성자가 쓴 **상한**이다. 일반 성능은 측정 불가.
반복(--repeat)마다 **발신 번호를 바꿔** 앞 회차 통화가 지난 통화로 섞이지 않게 한다.

  .venv/bin/python scripts/persona_sim/briefing_check.py --core-url http://localhost:8001 \
      --mediator-url ws://localhost:8081 --repeat 3 --ring-seconds 15
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "persona_sim" / "dasan-briefing"
REPLAY = ROOT / "services" / "call-mediator" / "scripts" / "replay_persona_call.ts"
OUT = ROOT / "data" / "processed" / "briefing"


def score(results: list[dict]) -> dict:
    by_source: dict[str, int] = defaultdict(int)
    cats: dict[str, set] = defaultdict(set)
    match = 0
    for r in results:
        by_source[r.get("source") or "none"] += 1
        cats[r["script"]].add(r.get("category"))
        if r.get("category") is not None and r.get("category") == r["expected"]:
            match += 1
    return {"n": len(results), "match": match, "by_source": dict(by_source),
            "unstable": sorted(s for s, c in cats.items() if len(c) > 1)}


def _replay(path: Path, call_id: str, phone: str, args, ring: int = 0, close: bool = True) -> subprocess.Popen:
    cmd = ["node", "--experimental-strip-types", str(REPLAY), str(path), "--url", args.mediator_url,
           "--call-id", call_id, "--speed", str(args.speed)]
    if close:
        cmd += ["--close", "--core-url", args.core_url]
    if ring:
        cmd += ["--ring-seconds", str(ring)]
    env = {**os.environ, "CALLER_PHONE": phone}
    return subprocess.Popen(cmd, cwd=REPLAY.parents[1], env=env)


def _briefing(core_url: str, call_id: str, deadline: float) -> tuple[dict | None, float]:
    token = os.environ.get("INGEST_SERVICE_TOKEN", "").strip()
    headers = {"authorization": f"Bearer {token}"} if token else {}
    t0 = time.monotonic()
    while time.monotonic() < deadline:
        req = urllib.request.Request(f"{core_url}/hub/calls/{call_id}/briefing", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read()), (time.monotonic() - t0) * 1000
        except urllib.error.HTTPError as e:
            if e.code != 404:   # 404 = 통화가 아직 안 만들어졌다 — 다시 본다
                raise
        time.sleep(0.3)
    return None, (time.monotonic() - t0) * 1000


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--core-url", default="http://localhost:8001")
    p.add_argument("--mediator-url", default="ws://localhost:8081")
    p.add_argument("--repeat", type=int, default=3)
    p.add_argument("--ring-seconds", type=int, default=15)
    p.add_argument("--speed", type=float, default=4.0)
    args = p.parse_args()

    scripts = {json.loads(f.read_text())["id"]: (f, json.loads(f.read_text())) for f in sorted(SCRIPTS.glob("SYN-*.json"))}
    currents = [(sid, s) for sid, (_, s) in scripts.items() if s.get("expected", {}).get("briefing", {}).get("role") == "current"]
    stamp = datetime.now().strftime("%Y%m%dT%H%M")
    results = []
    for run in range(1, args.repeat + 1):
        for k, (sid, script) in enumerate(currents):
            phone = f"010000{run:02d}{k:03d}"   # 회차·고객마다 다른 가짜 번호
            for prior_id in script["expected"]["briefing"]["prior"]:
                proc = _replay(scripts[prior_id][0], f"brief-{prior_id.lower()}-{stamp}-r{run}", phone, args)
                if proc.wait() != 0:
                    raise SystemExit(f"{prior_id} 재생 실패")
            call_id = f"brief-{sid.lower()}-{stamp}-r{run}"
            proc = _replay(scripts[sid][0], call_id, phone, args, ring=args.ring_seconds, close=False)
            body, ms = _briefing(args.core_url, call_id, time.monotonic() + args.ring_seconds)
            proc.wait()
            purpose = (body or {}).get("purpose") or {}
            results.append({"script": sid, "run": run, "expected": script["expected"]["briefing"]["purpose_category"],
                            "status": (body or {}).get("status"), "category": purpose.get("category"),
                            "source": purpose.get("source"), "text": purpose.get("text"),
                            "lines": (body or {}).get("briefing_lines"), "ms_until_ready": round(ms)})
            print(f"  r{run} {sid}: {purpose.get('category')} ({purpose.get('source')}) · 기대 {results[-1]['expected']} · {round(ms)}ms")
    s = score(results)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"briefing-check-{stamp}.json"
    out.write_text(json.dumps({"score": s, "results": results, "args": vars(args), "source": "synthetic"},
                              ensure_ascii=False, indent=1))
    print(f"\n{s['match']}/{s['n']} 일치 · 출처 {s['by_source']} · 흔들림 {s['unstable']} → {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: 통과 확인**

Run: `.venv/bin/python -m pytest scripts/persona_sim/tests/test_briefing_check.py -q`
Expected: 3 passed

- [ ] **Step 6: 커밋 — 대본·라벨을 채점보다 먼저 남긴다**

```bash
git add scripts/persona_sim/dasan-briefing
git commit -m "data(f3): 브리핑 대본 고객 셋 — 정답 목적은 실행 전에 라벨 (decisions/220)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git add scripts/persona_sim/briefing_check.py scripts/persona_sim/tests/test_briefing_check.py
git commit -m "code(f3): 브리핑 왕복 검사·범주 채점 (decisions/220)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: 로컬 스택 왕복 · 기록

**Files:**
- Modify: `jekyll/_backlogs/w8-f3-customer-briefing.md` (결과 절 · status)
- Create: `jekyll/_logs/2026-10-06-02-ryujun.md` (같은 날 다른 seq 가 이미 있으면 다음 번호)
- Modify: `_project/STATE.md` (`ai/` 줄만 덮어쓴다 — `decisions/101`)
- Modify: `jekyll/open-items.markdown` (남긴 것)
- Modify: `_project/decisions/220-…md` (「결과」 절 덧붙이기 — 앞 절은 고치지 않는다)

- [ ] **Step 1: 로컬 스택을 띄운다** — `scripts/persona_sim/E2E.md` §1 그대로(ES 9200 · Postgres 5434 `callguard_e2e` · 서버 :8001 · 미디에이터 :8081). ⚠ `RETRIEVAL_EMBED_MODEL_DIR` 는 **절대 경로**(E2E.md 경고). `CUSTOMER_REF_HMAC_KEY` 가 없으면 전부 `unidentified` 가 된다 — `/tmp/e2e.env` 에 있는지 확인. 모델 겹을 켜려면 `OLLAMA_URL=http://localhost:11434` · `POSTCALL_MODEL=kanana-1.5-2.1b-instruct:q4_k_m` 를 서버 env 에 넣고 `curl -s localhost:8001/health` 의 `spokes` 에 `briefing`·`briefing_model` 이 있는지 본다.

- [ ] **Step 2: 규칙만으로 한 번, 모델로 세 번 돌린다**

```bash
# 규칙만 (서버를 OLLAMA_URL 없이 띄운 상태)
(set -a; source /tmp/e2e.env; set +a; .venv/bin/python scripts/persona_sim/briefing_check.py --repeat 1)
# 모델 (OLLAMA_URL·POSTCALL_MODEL 넣고 서버 재기동 후)
(set -a; source /tmp/e2e.env; set +a; .venv/bin/python scripts/persona_sim/briefing_check.py --repeat 3)
```
Expected: 각 이번 통화에서 `status: ready` 가 벨 시간(15초) 안에 온다. 일치 수는 **나온 그대로** 적는다.

- [ ] **Step 3: 결과를 기록한다** — 숫자 그대로, 틀린 것도 그대로(절대 원칙 2·8):
  - 티켓 `w8-f3-customer-briefing.md` 「결과」 절: 측정일 · 커밋 · 명령 · 표본(대본 3 × 회차) · 규칙 일치 m/3 · 모델 일치 m/9 · 출처 분포 · 흔들린 대본 · 벨 안에 준비된 시간(최대 ms) · 「synthetic · 상한」
  - `decisions/220` 끝에 「결과 (2026-10-06)」 절을 **덧붙인다**
  - 진행 기록 새 파일 · `STATE.md` `ai/` 줄 · 미결(화면 카드 대기 · 실제 교환기 경로 · 일반 성능 측정 불가)
  - 완료 조건을 다 채웠으면 티켓 `status: "done"`

- [ ] **Step 4: 검증·커밋**

Run: `cd jekyll && bundle exec jekyll build && cd .. && python3 -X utf8 scripts/check_session_end.py`
Expected: 빌드 성공 · 「통과」

```bash
git add jekyll/_backlogs/w8-f3-customer-briefing.md jekyll/_logs _project/STATE.md jekyll/open-items.markdown _project/decisions/220-*.md
git commit -m "log(f3): 브리핑 왕복 실측 — 규칙/모델 범주 일치·벨 안 준비 시간 (decisions/220)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

**푸시·PR 은 하지 않는다** — 사용자에게 보고하고 지시를 기다린다.
