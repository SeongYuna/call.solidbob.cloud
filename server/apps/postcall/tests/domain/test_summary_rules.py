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


def test_유형은_지식베이스_장_어휘로_제안한다():
    """전에는 규칙표가 없어 늘 None 이었다(decisions/306). 지식베이스 장 어휘 규칙표가 생겼다(decisions/323) — 제안이지 확정이 아니다."""
    assert build_draft(CALL).inquiry_type == "일반행정"  # 「전입신고」 — TERM 4.4


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


def test_요약이_서류_후속조치_마무리까지_싣는다():
    """2026-09-23 — 채점(`decisions/218`)에서 서류 2/23 · 조치 1/10 이었다. 두 줄 발췌가 중·후반을 통째로 버렸다.

    고친 뒤 같은 하네스에서 핵심 항목 21/60 → 53/60(서류 23/23 · 조치 9/10)이다. 지어낸 문장은 없다 — 전부 발췌다.
    """
    us = [
        _u("customer", "주민등록초본을 떼려고 하는데 무엇이 필요한가요"),
        _u("agent", "네 고객님 초본 발급 도와드리겠습니다"),
        _u("agent", "신분증을 지참하셔서 방문해 주시고 대리인이면 위임장이 필요합니다"),
        _u("agent", "접수되면 문자로 연락드리겠습니다"),
        _u("agent", "그 밖에 궁금하신 점은 다시 전화 주시면 안내해 드립니다"),
    ]
    draft = build_draft(us)
    assert "필요서류 안내:" in draft.summary_text and "위임장" in draft.summary_text
    assert "후속 조치:" in draft.summary_text and "문자로 연락드리겠습니다" in draft.summary_text
    assert "마무리 안내:" in draft.summary_text
    # 발췌만 싣는다 — 요약의 각 조각이 실제 발화에 있어야 한다(환각 0, decisions/306)
    for line in draft.summary_text.split(" / "):
        if line.startswith("발화 "):
            continue
        body = line.split(": ", 1)[1]
        for piece in body.split(" · "):
            assert any(piece.rstrip("…") in u.text for u in us), piece


def test_서류_안내가_없으면_그_줄은_안_실린다():
    us = [_u("customer", "버스 노선을 알고 싶어서 전화드렸어요"), _u("agent", "몇 번 버스를 찾으시는지 말씀해 주세요")]
    draft = build_draft(us)
    assert "필요서류 안내:" not in draft.summary_text and "후속 조치:" not in draft.summary_text
