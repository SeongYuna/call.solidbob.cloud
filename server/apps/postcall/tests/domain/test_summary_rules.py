# Requirement: D-1, D-2, D-3, QUA-1
"""규칙 발췌 초안 — 지어낸 문장이 없고, 유형은 만들지 않고, 약속 발화만 후속조치로 뽑는다."""

from postcall.domain.services.summary_rules import (
    ACTION_MAX_CHARS,
    EXCERPT_MAX_CHARS,
    Utterance,
    build_draft,
)


def _u(speaker, text):
    return Utterance(speaker=speaker, text=text)


CALL = [
    _u("agent", "네 120 다산콜센터입니다"),
    _u("customer", "여보세요"),
    _u("customer", "전입신고 하려는데 어떤 서류가 필요한가요"),
    _u("agent", "네"),
    _u("agent", "신분증과 임대차계약서를 가지고 주민센터로 가시면 됩니다"),
    _u("agent", "필요서류 목록은 문자로 보내 드리겠습니다"),
    _u("agent", "감사합니다 좋은 하루 되세요"),
]


def test_고객의_첫_실질_발화와_그_뒤_상담원_안내를_발췌한다():
    s = build_draft(CALL).summary_text
    assert "고객 문의: 전입신고 하려는데 어떤 서류가 필요한가요" in s
    assert "상담원 안내: 신분증과 임대차계약서를 가지고 주민센터로 가시면 됩니다" in s
    assert "여보세요" not in s  # 인사는 문의가 아니다


def test_요약의_모든_발췌는_자막에_있는_글자다():
    """지어낸 문장이 없다 — 환각이 생길 자리가 없다(절대 원칙 9)."""
    s = build_draft(CALL).summary_text
    texts = {u.text for u in CALL}
    for part in s.split(" / ")[:-1]:
        _, excerpt = part.split(": ", 1)
        assert excerpt in texts


def test_발화_건수와_초안_표시가_붙는다():
    assert "발화 고객 2건 · 상담원 5건 (규칙 발췌 초안)" in build_draft(CALL).summary_text


def test_발췌할_발화가_없어도_요약이_비지_않는다():
    s = build_draft([_u("customer", "네"), _u("agent", "네")]).summary_text
    assert s == "발화 고객 1건 · 상담원 1건 (규칙 발췌 초안)"


def test_유형은_만들지_않는다():
    """유형을 가를 규칙표가 없다 — 없는 규칙으로 분류하지 않는다(decisions/306)."""
    assert build_draft(CALL).inquiry_type is None


def test_긴_발화는_잘라서_싣는다():
    long = "가" * (EXCERPT_MAX_CHARS + 50)
    s = build_draft([_u("customer", long)]).summary_text
    excerpt = s.split(" / ")[0].removeprefix("고객 문의: ")
    assert len(excerpt) == EXCERPT_MAX_CHARS and excerpt.endswith("…")


def test_상담원이_약속한_연락_발송만_후속조치다():
    assert build_draft(CALL).follow_up_actions == ("필요서류 목록은 문자로 보내 드리겠습니다",)


def test_통화_안에서_끝나는_약속은_후속조치가_아니다():
    assert build_draft([_u("agent", "분실 신고 도와드리겠습니다")]).follow_up_actions == ()


def test_고객의_약속은_후속조치가_아니다():
    assert build_draft([_u("customer", "제가 다시 전화 드리겠습니다")]).follow_up_actions == ()


def test_띄어쓰기가_달라도_잡고_같은_약속은_한_번만():
    actions = build_draft([
        _u("agent", "담당 부서에 전달해드리겠습니다"),
        _u("agent", "담당 부서에 전달해드리겠습니다"),
        _u("agent", "확인 후 회신 드릴게요"),
    ]).follow_up_actions
    assert actions == ("담당 부서에 전달해드리겠습니다", "확인 후 회신 드릴게요")


def test_후속조치는_DB_컬럼_길이를_넘지_않는다():
    long = "문자로 보내 드리겠습니다 " + "가" * 300
    (action,) = build_draft([_u("agent", long)]).follow_up_actions
    assert len(action) == ACTION_MAX_CHARS
