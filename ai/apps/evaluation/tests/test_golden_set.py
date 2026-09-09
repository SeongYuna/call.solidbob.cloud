# Requirement: E-1
"""골든셋 로더.

2026-08-28 다산콜센터 단일 도메인으로 전환했다(`_project/decisions/201`).
금융보험·쇼핑·질병관리본부 항목과 그에 딸린 F-2 케이스가 전부 빠졌다 —
다산은 정보 안내형이라 종결 처리 유형이 없다(`knowledge-base/dasan/policy/POLICY.md`).
"""

from evaluation.golden_set import load_golden_set


def test_다산_10건을_읽는다():
    items = load_golden_set()
    assert len(items) == 10
    assert all(it.domain == "dasan" for it in items)


def test_도메인이_다산_하나뿐이다():
    """단일 도메인 전환의 회귀 방지 — 다른 도메인이 되살아나면 여기서 걸린다."""
    assert {it.domain for it in load_golden_set()} == {"dasan"}


def test_F2_케이스가_없다():
    """다산은 종결 처리 유형이 없어 F-2 를 적용하지 않는다(POLICY-1).

    ⚠ 필요서류 체크리스트로 F-2 게이트를 전용하기로 했으므로(`decisions/201`),
    그 케이스가 만들어지면 이 테스트를 바꿔야 한다 — 지금은 없는 것이 정상이다.
    """
    assert all(it.f2_case is None for it in load_golden_set())


def test_PII_패턴이_마스킹_케이스에_붙는다():
    items = {it.id: it for it in load_golden_set()}
    pii = [it for it in items.values() if it.pii_patterns]
    assert pii, "C-5 채점 표본이 하나도 없다"
    assert all(p.masked_expected for it in pii for p in it.pii_patterns)


def test_검색_케이스는_다산_조항을_가리킨다():
    """정답 문서 ID 가 남아 있는 지식베이스(다산 20조항)를 벗어나면 영원히 못 맞힌다."""
    expected = {d for it in load_golden_set() for d in it.expected_doc_ids}
    assert expected, "검색 채점 표본이 없다"
    assert all(d.startswith("DASAN-") for d in expected), sorted(expected)
