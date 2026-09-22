# Requirement: C-5, QUA-1
"""중간 자막(interim) 전용 — 번호가 다 들어오기 전의 숫자 덩어리를 가린다(미결 「C-5 중간 자막」, 09-22).

확정 규칙은 완성된 번호(휴대전화 10~11자리·카드 14~16자리 …)만 잡는다. 중간 자막은 번호가 **들어오는 중**이라
`9410 0000`(8자리)·`010 0000`(7자리)이 어느 패턴에도 안 맞아 **화면에 그대로 나갔다**(표본 6건 중 5건).
중간 자막은 곧 확정 자막으로 바뀌므로 넓게 가린다 — 절대 원칙 3 「애매하면 가린다」.
"""

import pytest

from masking.domain.services.interim_digit_guard import guard_interim


@pytest.mark.parametrize("text, expected", [
    ("카드번호 9410 0000", "카드번호 **** ****"),
    ("전화번호는 010 0000", "전화번호는 *** ****"),
    ("010-12", "***-**"),                     # 구분자 뒤 두 자리도 앞 덩어리와 이어진 번호다
    ("공일공 공공공", "*** ***"),               # 낭독형도 같다
])
def test_번호가_다_들어오기_전의_숫자_덩어리를_가린다(text, expected):
    assert guard_interim(text)[0] == expected


@pytest.mark.parametrize("text", ["서류 2개 가져오세요", "30분 뒤에", "3시에 오세요", "이미 *** 로 가렸다"])
def test_두_자리_이하와_이미_가린_글자는_그대로다(text):
    """자막이 읽혀야 한다 — 수량·시각까지 지우지 않는다(P5 가 문맥 없는 4자리를 안 가리는 것과 같은 이유)."""
    assert guard_interim(text) == (text, ())


def test_자릿수를_보존하고_구간을_돌려준다():
    masked, spans = guard_interim("카드 9410 0000 이요")
    assert len(masked) == len("카드 9410 0000 이요")
    assert [(s.start, s.end) for s in spans] == [(3, 12)]


@pytest.mark.parametrize("text, pattern", [
    ("카드번호 9410 0000", "P2"),   # 문맥어가 있으면 그 패턴
    ("계좌 1234 567", "P3"),
    ("010 0000", "P4"),            # 0 으로 시작하면 전화번호로 부른다
    ("9410 0000", "P3"),           # 문맥 없으면 가장 넓은 숫자 패턴(계좌 10~14)
])
def test_라벨은_P1_P7_안에서_고른다(text, pattern):
    """새 패턴을 만들지 않는다(`pii_pattern.py`) — 프론트 계약도 P1~P7 뿐이다."""
    assert guard_interim(text)[1][0].pattern == pattern
