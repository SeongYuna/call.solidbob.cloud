# Requirement: E-1, E-2, E-4, QUA-1
"""하네스 배선(wiring) 검증. 실제 검색/트리거/컴플라이언스/마스킹/게이트 스포크는 아직
없으므로, ①전부 미구현 상태에서 크래시 없이 "N/A"를 정직하게 보고하는지, ②hub 포트를
구현한 가짜 객체를 꽂았을 때 golden-set → metrics로 데이터가 올바르게 흘러가는지 두 가지만
확인한다. 실제 정확도 수치를 여기서 하드코딩하지 않는다 (6.2절 원칙 5)."""

from evaluation.golden_set import load_golden_set
from evaluation.harness import NO_SAMPLES, NOT_IMPLEMENTED, Ports, run_eval
from hub.app.dtos import ClosureVerdict, DomainClassification, MaskedSpan, TranscriptEvent, TriggerDecision
from hub.app.ports.output import ClosureGatePort, DomainRoutingPort, MaskingPort, TriggerPort


def test_all_ports_none_reports_not_implemented():
    items = load_golden_set()
    report = run_eval(items, Ports())
    for section in ("domain_routing", "retrieval", "trigger", "compliance", "masking", "closure_gate"):
        assert report[section] == "측정 불가 — 모듈 미구현"


class _EchoDomainRouting(DomainRoutingPort):
    """발화 안에 도메인 이름이 그대로 있으면 정답을 맞히는 가짜 포트 — 배선만 검증한다."""

    async def classify(self, utterance: str) -> DomainClassification:
        for domain in ("finance", "dasan", "shopping", "health"):
            if domain in utterance:
                return DomainClassification(domain=domain, confidence=1.0)
        return DomainClassification(domain="finance", confidence=0.0)  # 못 찾으면 임의 기본값


def test_도메인_라우팅은_더_이상_채점하지_않는다():
    """2026-08-28 단일 도메인 전환(`decisions/201`) — 도메인이 하나면 라우팅이 없다.

    허브 포트는 계약으로 남아 있지만 `ai/` 쪽 구현체를 지웠으므로 항상 "미구현"이다.
    골든셋의 `domain` 필드도 전부 `dasan` 이라 채점 대상 자체가 성립하지 않는다.
    """
    report = run_eval(load_golden_set(), Ports())
    assert report["domain_routing"] == NOT_IMPLEMENTED


class _PerfectClosureGate(ClosureGatePort):
    """골든셋의 기대값을 그대로 돌려주는 가짜 포트 구현 — 배선만 검증한다."""

    def evaluate(self, call_id, closure_type, evidence, reason=None) -> ClosureVerdict:
        missing = tuple(field for field, ok in evidence.items() if not ok)
        return ClosureVerdict(
            call_id=call_id, closure_type=closure_type, evidence=evidence,
            verdict="approved" if not missing else "blocked", missing=missing,
        )


def test_F2_는_다산에_채점할_케이스가_없다():
    """다산은 정보 안내형이라 종결 처리 유형이 없다(`POLICY-1`).

    스포크를 꽂아도 채점할 항목이 0건이다. **"통과"가 아니라 "잴 것이 없다"** 이고,
    그 둘을 구분해 보고하는지 확인한다(절대 원칙 10).

    ⚠ 2026-08-28: 이 단언이 원래 `result == NOT_IMPLEMENTED or result.get("n") == 0` 이었다.
    **docstring 이 약속한 「구분」을 실제로는 검증하지 않았고**, 그때 하네스는 빈 입력에
    `absolute_rule_passed: True` 를 내고 있었다 — 가짜 만점이 그대로 통과했다.
    이제 세 상태(미구현 / 표본 없음 / 채점됨)를 서로 다른 값으로 본다.
    """
    report = run_eval(load_golden_set(), Ports(closure_gate=_PerfectClosureGate()))
    assert report["closure_gate"] == NO_SAMPLES, report["closure_gate"]


def test_스포크가_없는_것과_표본이_없는_것을_구분한다():
    """둘 다 「측정 불가」지만 다음에 할 일이 다르다 — 만들 것인가, 골든셋을 채울 것인가."""
    no_spoke = run_eval(load_golden_set(), Ports())["closure_gate"]
    no_samples = run_eval(load_golden_set(), Ports(closure_gate=_PerfectClosureGate()))["closure_gate"]
    assert no_spoke == NOT_IMPLEMENTED
    assert no_samples == NO_SAMPLES
    assert no_spoke != no_samples


class _FixedDelayTrigger(TriggerPort):
    """항상 발화 종료 900ms 뒤에 발동하는 가짜 포트 — 배선과 지연 분포 계산만 검증한다."""

    def decide(self, event: TranscriptEvent) -> TriggerDecision:
        return TriggerDecision(fire=True, at_ms=event.utterance_end_ms + 900)


def test_trigger_wiring_reports_latency_distribution():
    items = load_golden_set()
    report = run_eval(items, Ports(trigger=_FixedDelayTrigger()))
    result = report["trigger"]
    assert result["n"] == 6  # utterance_end_ms 가 있는 B 케이스 6건 (2026-08-28 재구성)
    assert result["on_time_rate"] == 1.0  # 900ms는 0~1,500ms 허용 창 안
    assert result["latency_ms"]["p50"] == 900
    assert result["latency_ms"]["p95"] == 900
    assert result["latency_ms"]["n"] == 6
    assert result["not_fired"] == 0


class _DigitsOnlyMasking(MaskingPort):
    """연속 숫자 11자리(P4)만 가리는 가짜 — 절대 규칙이 '1건 누락 = 실패'로 뚫리는지 배선 검증."""

    def mask(self, text: str):
        idx = text.find("01012345678")
        if idx < 0:
            return text, ()
        return text[:idx] + "*" * 11 + text[idx + 11:], (MaskedSpan(type="P4", span=(idx, idx + 11)),)


def test_masking_wiring_reports_misses_per_pattern():
    items = load_golden_set()
    result = run_eval(items, Ports(masking=_DigitsOnlyMasking()))["masking"]
    # 숫자만 가리는 가짜 마스킹이라 P6(인명)·P7(상세주소)을 놓친다.
    # 2026-08-28 단일 도메인 전환으로 표본이 바뀌었다 — 항목 ID 를 하드코딩하지 않고
    # "숫자가 아닌 패턴은 전부 놓친다"는 성질로 검증한다. 골든셋이 늘어도 안 깨진다.
    assert result["absolute_rule_passed"] is False
    assert result["miss_count"] > 0
    non_digit = {p.pattern for it in items for p in it.pii_patterns if p.pattern in ("P6", "P7")}
    assert non_digit, "숫자가 아닌 PII 표본이 없어 이 테스트가 아무것도 검증하지 못한다"
