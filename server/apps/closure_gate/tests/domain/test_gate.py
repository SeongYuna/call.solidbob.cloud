# Requirement: F-2, QUA-1
"""필요서류 체크리스트 판정. **필수 서류가 하나라도 빠지면 빠짐없이 `missing` 에** — 절대 규칙이라 여기서 먼저 깨진다.

규칙표의 출처는 다산 필요서류 조항(`DASAN-TERM-*`)이다 — 이 테스트가 보는 것은 "판정이 규칙표대로인가"이고,
"규칙표가 조항과 같은가"는 `test_closure_rule_source.py` 가 본다.
"""

import pytest

from closure_gate.domain.services.gate import UnknownProcedure, evaluate
from closure_gate.domain.value_objects.closure_rule import EXCLUDED, RULES

ALL_TRUE = {p: {d.name: True for d in r.required} for p, r in RULES.items()}


@pytest.mark.parametrize("procedure", list(RULES))
def test_필수_서류를_전부_안내했을_때만_complete(procedure):
    d = evaluate(procedure, ALL_TRUE[procedure])
    assert d.verdict == "complete" and d.missing == ()


@pytest.mark.parametrize("procedure, drop", [(p, d.name) for p, r in RULES.items() for d in r.required])
def test_하나라도_빠지면_incomplete_이고_그것만_missing(procedure, drop):
    evidence = {**ALL_TRUE[procedure], drop: False}
    d = evaluate(procedure, evidence)
    assert d.verdict == "incomplete" and d.missing == (drop,)


@pytest.mark.parametrize("procedure", list(RULES))
def test_키가_없거나_참이_아닌_값은_안내하지_않은_것이다(procedure):
    """애매하면 누락으로 잡는다 — `1`·`"yes"` 를 참으로 세지 않는다."""
    rule = RULES[procedure]
    d = evaluate(procedure, {rule.required[0].name: "yes"})
    assert d.verdict == "incomplete"
    assert d.missing == tuple(doc.name for doc in rule.required)  # 규칙표 순서 그대로


def test_규칙_없는_절차는_판정하지_않고_거절한다():
    with pytest.raises(UnknownProcedure):
        evaluate("DASAN-TERM-9.9", {"신분증": True})


@pytest.mark.parametrize("procedure", list(EXCLUDED))
def test_제외한_조항은_이유와_함께_거절한다(procedure):
    with pytest.raises(UnknownProcedure, match=EXCLUDED[procedure][:10]):
        evaluate(procedure, {"신분증": True})


def test_규칙과_제외가_겹치지_않는다():
    assert not set(RULES) & set(EXCLUDED)
