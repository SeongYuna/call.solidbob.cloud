# Requirement: E-1
"""골든셋 로더.

2026-08-28 다산콜센터 단일 도메인으로 전환했다(`_project/decisions/201`).
금융보험·쇼핑·질병관리본부 항목과 그에 딸린 F-2 케이스가 전부 빠졌다 —
다산은 정보 안내형이라 종결 처리 유형이 없다(`knowledge-base/dasan/policy/POLICY.md`).

2026-09-09 기본 골든셋이 `v1-150.json`(156건)이 됐다(`w3-golden-set-dasan`).
**크기를 못박는 테스트를 쓰지 않는다** — 골든셋은 앞으로도 늘어나는데 숫자를 박아 두면
항목을 더할 때마다 여기가 깨지고, 그러면 「테스트를 고치는 김에」 표본 요건까지 같이
느슨해진다. 대신 **최소 규모와 구성**을 본다.
"""

from evaluation.golden_set import load_golden_set


def test_공식_골든셋은_150건_이상이다():
    """3주차 목표치(`w3-golden-set-dasan`). 13건으로는 1건이 7.7%p 를 움직여
    Recall@5·MRR 을 신뢰할 수 없었다."""
    items = load_golden_set()
    assert len(items) >= 150
    assert all(it.domain == "dasan" for it in items)


def test_필요서류_케이스가_30건_이상이다():
    """새 메인 기능이 「필요서류 제시」다(`decisions/201`). 이게 얇으면 B 를 재는 것이
    아니라 일반 안내 검색을 재게 된다."""
    items = load_golden_set()
    doc_clauses = {
        "DASAN-TERM-1.3", "DASAN-TERM-1.4", "DASAN-TERM-2.2", "DASAN-TERM-2.5",
        "DASAN-TERM-2.6", "DASAN-TERM-2.7", "DASAN-TERM-2.9", "DASAN-TERM-3.4",
        "DASAN-TERM-3.5", "DASAN-TERM-3.6", "DASAN-TERM-3.7", "DASAN-TERM-3.8",
        "DASAN-TERM-3.10", "DASAN-TERM-3.14", "DASAN-TERM-4.1", "DASAN-TERM-4.3",
        "DASAN-TERM-4.4", "DASAN-TERM-4.5", "DASAN-TERM-4.6", "DASAN-TERM-4.9",
        "DASAN-TERM-4.11", "DASAN-TERM-4.12", "DASAN-TERM-4.13", "DASAN-TERM-4.14",
        "DASAN-TERM-4.16", "DASAN-TERM-4.17", "DASAN-TERM-4.18", "DASAN-TERM-4.20",
        "DASAN-TERM-5.8", "DASAN-TERM-5.9", "DASAN-TERM-6.2", "DASAN-TERM-6.3",
        "DASAN-TERM-6.4", "DASAN-TERM-6.5", "DASAN-TERM-6.6", "DASAN-TERM-6.7",
        "DASAN-TERM-6.8", "DASAN-TERM-6.9",
    }
    cases = [it for it in items
             if it.module == "B" and doc_clauses & set(it.expected_doc_ids)]
    assert len(cases) >= 30, f"필요서류 케이스가 {len(cases)}건뿐이다"


def test_P1부터_P7까지_전부_표본이_있다():
    """⚠ 2026-08-28 까지 C-5 「누락 0건 통과」는 **P4·P6·P7 세 패턴 위에서** 낸 값이었다.
    나머지 넷은 표본이 0건이라 판정된 적이 없다(절대 원칙 10). 여기서 그것을 막는다."""
    patterns = {p.pattern for it in load_golden_set() for p in it.pii_patterns}
    assert patterns >= {f"P{i}" for i in range(1, 8)}, sorted(patterns)


def test_C6_케이스에_정상_발화가_섞여_있다():
    """폭언만 실으면 「전부 폭언」이라고 답하는 구현이 재현율 만점을 받는다(절대 원칙 10)."""
    c6 = [it for it in load_golden_set() if it.module == "C-6"]
    assert c6, "C-6 채점 표본이 없다"
    assert any(it.call_guard is None for it in c6), "정상 발화가 하나도 없다"
    assert any(it.call_guard and it.call_guard.type == "distress" for it in c6), (
        "위기 신호(distress) 표본이 없다 — 5.4 조는 폭언과 다르게 다루라고 정한다"
    )


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
    assert any(p.masked_expected for it in pii for p in it.pii_patterns)


def test_과잉_마스킹을_잡을_음성_케이스가_있다():
    """`masked_expected: false` 항목이 없으면 과잉 마스킹률이 계산되지 않는다(nan).
    「금액·연도·번지수를 가리지 않는다」를 재는 자리다."""
    negatives = [p for it in load_golden_set() for p in it.pii_patterns
                 if not p.masked_expected]
    assert negatives, "음성 케이스가 없어 과잉 마스킹을 잴 수 없다"


def test_검색_케이스는_다산_조항을_가리킨다():
    """정답 문서 ID 가 지식베이스(다산 98조항)를 벗어나면 영원히 못 맞힌다."""
    expected = {d for it in load_golden_set() for d in it.expected_doc_ids}
    assert expected, "검색 채점 표본이 없다"
    assert all(d.startswith("DASAN-") for d in expected), sorted(expected)
