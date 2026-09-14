# Requirement: F-2
"""판정 ③ — 필요서류 체크리스트. **규칙이 판정한다. 생성 모델은 여기 없다** (절대 원칙 9).

절대 규칙: **필수 서류가 하나라도 안내되지 않았으면 `incomplete` — 빠짐없이 `missing` 에 싣는다.**
[6.2절](/docs/06/)대로 평균이 아니라 건 단위다.

rev.5(`plan.md` 7.3절) — **차단이 아니라 경고**다. 다산에는 막을 종결 행위가 없고, 서류를 빠뜨리면 시민이 헛걸음한다.

**주장 범위를 넘지 않는다.** 이 게이트는 *"안내 누락의 비용을 올린다"* 는 목적이지 *"안내가 정확했다"* 를 보증하지
않는다([부록 A-3](/docs/12/)). 입력(`evidence`)이 틀리면 판정도 틀린다.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..value_objects.closure_rule import EXCLUDED, RULES, ClosureRule


class UnknownProcedure(ValueError):
    """규칙표에 없는 절차. **판정하지 않고 거절한다.**

    `complete` 는 절대 규칙 위반이고, `incomplete` 도 거짓말이다 — "서류가 빠졌다"가 아니라
    "판정할 규칙이 없다"이기 때문이다. 요청 오류(422)로 돌려보낸다.
    """


@dataclass(frozen=True)
class GateDecision:
    verdict: str  # "complete" | "incomplete"
    missing: tuple[str, ...]
    rule: ClosureRule


def rule_for(procedure: str) -> ClosureRule:
    rule = RULES.get(procedure)
    if rule is None:
        why = EXCLUDED.get(procedure)
        raise UnknownProcedure(
            f"'{procedure}' 은 규칙을 만들지 않은 필요서류 조항입니다 — {why}" if why
            else f"'{procedure}' 은 필요서류 체크리스트 규칙이 없는 절차입니다"
        )
    return rule


def evaluate(procedure: str, evidence: dict[str, bool]) -> GateDecision:
    """절차의 필수 서류가 전부 `True` 일 때만 `complete`.

    **값이 없으면 안내하지 않은 것으로 본다.** 키가 빠진 경우와 `false` 를 구분하지 않는다 — 둘 다 "안내했다는
    근거가 없다"이고, 애매하면 누락으로 잡는다. `True` 인지 **엄격하게** 본다(`1`·`"yes"` 를 참으로 세지 않는다).
    """
    rule = rule_for(procedure)
    missing = tuple(doc.name for doc in rule.required if evidence.get(doc.name) is not True)
    return GateDecision(verdict="incomplete" if missing else "complete", missing=missing, rule=rule)
