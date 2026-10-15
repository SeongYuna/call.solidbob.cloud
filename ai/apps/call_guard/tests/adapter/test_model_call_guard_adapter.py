# Requirement: C-6
import asyncio

from call_guard.adapter.outbound.model_call_guard_adapter import ModelCallGuardAdapter
from call_guard.adapter.outbound.rule_call_guard_adapter import RuleCallGuardAdapter
from call_guard.domain.services.mask_tokens import strip_mask_tokens


class _Clf:
    def __init__(self, verdict=True, fail=False):
        self.verdict, self.fail, self.seen = verdict, fail, []

    def __call__(self, text):
        self.seen.append(text)
        if self.fail:
            raise RuntimeError("down")
        return self.verdict


def _run(adapter, text):
    return asyncio.run(adapter.detect(text))


def test_rule_hit_is_kept_and_classifier_not_called():
    clf = _Clf()
    flags = _run(ModelCallGuardAdapter(RuleCallGuardAdapter(), clf), "이 멍청한 놈아")
    assert any(f.category == "insult" for f in flags) and clf.seen == []


def test_classifier_adds_insult_when_rule_misses():
    flags = _run(ModelCallGuardAdapter(RuleCallGuardAdapter(), _Clf(True)), "너 같은 건 상담할 자격도 없어")
    assert [f.category for f in flags] == ["insult"]
    assert flags[0].span == (0, len("너 같은 건 상담할 자격도 없어")) and flags[0].source_doc_id == "DASAN-MANUAL-5.1"


def test_classifier_negative_adds_nothing():
    assert _run(ModelCallGuardAdapter(RuleCallGuardAdapter(), _Clf(False)), "등본 떼려고요") == []


def test_classifier_failure_falls_back_to_rule():
    a = ModelCallGuardAdapter(RuleCallGuardAdapter(), _Clf(fail=True))
    assert _run(a, "등본 떼려고요") == [] and a.classifier_failures == 1


def test_distress_stays_and_classifier_can_still_add():
    flags = _run(ModelCallGuardAdapter(RuleCallGuardAdapter(), _Clf(True)), "요즘 너무 힘들어서 다 끝내고 싶어요")
    cats = [f.category for f in flags]
    assert "distress" in cats


def test_mask_tokens_are_stripped_before_classifier():
    clf = _Clf(False)
    _run(ModelCallGuardAdapter(RuleCallGuardAdapter(), clf), "제 번호는 ***-****-**** 이에요")
    assert "*" not in clf.seen[0]
    assert strip_mask_tokens("OOO-OOOO-OOOO입니다.") == "입니다."
    assert strip_mask_tokens("***") == ""


def test_no_classifier_is_rule_only():
    assert _run(ModelCallGuardAdapter(RuleCallGuardAdapter(), None), "너 같은 건 자격도 없어") == []
