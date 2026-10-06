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
