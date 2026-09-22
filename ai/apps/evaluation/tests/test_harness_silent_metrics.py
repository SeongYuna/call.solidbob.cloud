# Requirement: E-1, E-4, B-4, B-5, A-5, D-5, QUA-1
"""`w6-harness-silent-metrics` — 채점기는 있는데 하네스가 부르지 않던 지표가 **리포트에 줄로 나오는지**.

세 가지를 본다.
① 셋(`generation` B-4·B-5 · `asr` A-5 · `call_temperature` D-5)이 **어떤 포트 구성에서도** 리포트에 있다.
② 값이 없을 때는 사유가 붙은 「측정 불가」이고, 「미구현」·「표본 없음」·「꽂지 않음」이 서로 섞이지 않는다.
③ **기존 섹션의 순서와 값이 바뀌지 않는다**(회귀) — 새 섹션은 맨 뒤에만 붙고, 생성 포트를 꽂든 안 꽂든
   다른 섹션 값은 같다.

실제 정확도 수치를 여기서 하드코딩하지 않는다 — 가짜 포트로 배선만 본다(6.2절 원칙 5).
"""

from __future__ import annotations

import math

from evaluation.golden_set import GoldenItem, PiiPattern, load_golden_set
from evaluation.harness import (
    ASR_NOT_WIRED,
    GENERATION_NO_RETRIEVAL,
    GENERATION_NOT_PLUGGED,
    NO_SAMPLES,
    NOT_IMPLEMENTED,
    Ports,
    run_eval,
)
from evaluation.metrics import generation as generation_metrics
from hub.app.dtos import Card, MaskedSpan, RetrievedDoc, Source
from hub.app.ports.output import GenerationPort, MaskingPort, RetrievalPort

# 2026-09-22 이전 하네스가 내던 섹션과 그 순서. **이 목록을 고쳐야 테스트가 통과한다면 기존 리포트가 바뀐 것이다.**
EXISTING_SECTIONS = [
    "domain_routing", "retrieval", "no_answer", "trigger", "compliance",
    "call_guard", "masking", "closure_gate", "call_temperature",
]
NEW_SECTIONS = ["generation", "asr"]

_SNIPPET = "구비서류: 신분증, 전입신고서. 세대주 확인이 필요하다."


class _OneDocRetrieval(RetrievalPort):
    async def retrieve(self, utterance: str, top_k: int = 5) -> list[RetrievedDoc]:
        return [RetrievedDoc(doc_id="DASAN-TERM-4.4", title="전입신고", snippet=_SNIPPET, score=1.0)]


class _EmptyRetrieval(RetrievalPort):
    async def retrieve(self, utterance: str, top_k: int = 5) -> list[RetrievedDoc]:
        return []


class _ListCardGeneration(GenerationPort):
    """근거에 있는 서류 하나 + **근거에 없는 서류 하나**(`가족관계증명서`)를 실은 카드를 낸다 — 환각 1장."""

    async def to_cards(self, utterance: str, docs: list[RetrievedDoc]) -> list[Card]:
        return [
            Card(title=d.title, summary="필요 서류: 신분증 · 가족관계증명서",
                 source=Source(doc_id=d.doc_id, title=d.title), similarity_score=d.score)
            for d in docs
        ]


class _SnippetGeneration(GenerationPort):
    """스니펫 폴백과 같다 — 원문 그대로라 환각이 0 이어야 한다."""

    async def to_cards(self, utterance: str, docs: list[RetrievedDoc]) -> list[Card]:
        return [
            Card(title=d.title, summary=d.snippet, source=Source(doc_id=d.doc_id, title=d.title), similarity_score=d.score)
            for d in docs
        ]


class _DigitsMasking(MaskingPort):
    def mask(self, text: str) -> tuple[str, list[MaskedSpan]]:
        masked = "".join("*" if c.isdigit() else c for c in text)
        spans = [MaskedSpan(type="P4", span=(0, len(text)))] if masked != text else []
        return masked, spans


def _b_item(item_id: str) -> GoldenItem:
    return GoldenItem(id=item_id, module="B", domain="dasan", customer_utterance="전입신고 서류가 뭐예요",
                      expected_doc_ids=["DASAN-TERM-4.4"])


# ── ① 셋이 언제나 줄로 나온다 ────────────────────────────────────────────────


def test_포트를_하나도_안_꽂아도_세_지표가_리포트에_줄로_나온다():
    report = run_eval(load_golden_set(), Ports())
    for section in ("generation", "asr", "call_temperature"):
        assert section in report, f"{section} 가 리포트에서 조용히 빠졌다"
        assert isinstance(report[section], str) and report[section].startswith("측정 불가 — ")


def test_사유가_붙은_측정_불가는_미구현_표본없음과_섞이지_않는다():
    reasons = {GENERATION_NOT_PLUGGED, GENERATION_NO_RETRIEVAL, ASR_NOT_WIRED, NO_SAMPLES, NOT_IMPLEMENTED}
    assert len(reasons) == 5, "사유 문자열이 서로 같아 구분이 사라졌다"
    for r in (GENERATION_NOT_PLUGGED, GENERATION_NO_RETRIEVAL, ASR_NOT_WIRED):
        assert r.startswith("측정 불가 — ")


# ── ② B-4·B-5 생성 ──────────────────────────────────────────────────────────


def test_생성_포트가_없으면_꽂지_않았다고_찍는다():
    report = run_eval([_b_item("B-1")], Ports(retrieval=_OneDocRetrieval()))
    assert report["generation"] == GENERATION_NOT_PLUGGED


def test_생성은_꽂혔는데_검색이_없으면_근거가_없다고_찍는다():
    report = run_eval([_b_item("B-1")], Ports(generation=_ListCardGeneration()))
    assert report["generation"] == GENERATION_NO_RETRIEVAL


def test_생성과_검색을_꽂아도_B_항목이_없으면_NO_SAMPLES_다():
    item = GoldenItem(id="C6-1", module="C-6", domain="dasan", customer_utterance="…")
    report = run_eval([item], Ports(retrieval=_OneDocRetrieval(), generation=_ListCardGeneration()))
    assert report["generation"] == NO_SAMPLES


def test_생성을_꽂으면_화면에_나간_카드를_규칙으로_센다():
    items = [_b_item("B-1"), _b_item("B-2")]
    result = run_eval(items, Ports(retrieval=_OneDocRetrieval(), generation=_ListCardGeneration()))["generation"]
    assert result["questions"] == 2 and result["no_docs_questions"] == 0
    assert result["cards"] == 2
    assert result["source_rate"] == 1.0
    assert result["shipped_hallucinated_cards"] == 2  # 가족관계증명서는 근거 조항에 없다
    assert result["forbidden_cards"] == 0


def test_스니펫_카드는_환각이_0이다():
    result = run_eval([_b_item("B-1")], Ports(retrieval=_OneDocRetrieval(), generation=_SnippetGeneration()))["generation"]
    assert result["shipped_hallucinated_cards"] == 0


def test_포트로는_원출력_환각을_0으로_지어내지_않는다():
    """포트는 모델 원출력을 돌려주지 않는다 — 그 칸이 숫자 0 으로 나오면 잰 적 없는 0 이다(절대 원칙 2)."""
    result = run_eval([_b_item("B-1")], Ports(retrieval=_OneDocRetrieval(), generation=_ListCardGeneration()))["generation"]
    assert result["raw_hallucinated_cards"] == generation_metrics.RAW_NOT_AVAILABLE
    assert result["outcomes"] == generation_metrics.RAW_NOT_AVAILABLE


def test_검색이_빈_결과면_카드가_0장이고_출처_표시율은_nan이다():
    result = run_eval([_b_item("B-1")], Ports(retrieval=_EmptyRetrieval(), generation=_ListCardGeneration()))["generation"]
    assert result["no_docs_questions"] == 1 and result["cards"] == 0
    assert math.isnan(result["source_rate"]), "카드 0장에서 출처 표시율을 0 이나 1 로 지어냈다"


def test_score_shipped_cards_는_score_generation_과_같은_규칙으로_센다():
    rows = [
        {"doc_id": "T-1", "summary": "필요 서류: 신분증 · 여권", "source_text": _SNIPPET, "raw_output": "", "outcome": "generated"},
        {"doc_id": "T-2", "summary": "확실히 됩니다", "source_text": _SNIPPET, "raw_output": "", "outcome": "none"},
        {"doc_id": "", "summary": _SNIPPET, "source_text": _SNIPPET, "raw_output": "", "outcome": "none"},
    ]
    full, shipped = generation_metrics.score_generation(rows), generation_metrics.score_shipped_cards(rows)
    for key in ("cards", "source_rate", "shipped_hallucinated_cards", "forbidden_cards"):
        assert shipped[key] == full[key], key


# ── A-5 ─────────────────────────────────────────────────────────────────────


def test_A5_는_어떤_포트를_꽂아도_사유가_붙은_측정_불가다():
    report = run_eval([_b_item("B-1")], Ports(retrieval=_OneDocRetrieval(), generation=_SnippetGeneration()))
    assert report["asr"] == ASR_NOT_WIRED
    assert "measure_a5_proficiency" in ASR_NOT_WIRED, "따로 재는 곳을 가리키지 않으면 다음 사람이 찾지 못한다"


# ── ③ 회귀 — 기존 출력은 그대로다 ─────────────────────────────────────────────


def test_새_섹션은_맨_뒤에만_붙고_기존_섹션_순서는_그대로다():
    report = run_eval(load_golden_set(), Ports())
    # 2026-09-22 D-1·D-2 `postcall` 이 그 뒤에 붙었다(`w6-postcall-golden-cases`) — 앞 순서는 그대로다
    assert list(report) == EXISTING_SECTIONS + NEW_SECTIONS + ["postcall"]


def test_생성_포트를_꽂아도_기존_섹션_값은_한_글자도_안_바뀐다():
    pii = PiiPattern(pattern="P4", raw_span="01012345678", masked_expected=True)
    items = [
        _b_item("B-1"),
        GoldenItem(id="P-1", module="C-5", domain="dasan", customer_utterance="번호는 01012345678", pii_patterns=[pii]),
    ]
    base = Ports(retrieval=_OneDocRetrieval(), masking=_DigitsMasking())
    without = run_eval(items, base)
    with_gen = run_eval(items, Ports(retrieval=_OneDocRetrieval(), masking=_DigitsMasking(), generation=_ListCardGeneration()))
    for section in EXISTING_SECTIONS:
        assert repr(with_gen[section]) == repr(without[section]), section  # repr — nan != nan 이라 == 로는 못 댄다


def test_기존_섹션_값_스냅숏():
    """합성 항목 두 건으로 낸 기존 섹션 값을 그대로 박아 둔다 — 새 배선이 기존 계산에 손대면 여기서 깨진다."""
    pii = PiiPattern(pattern="P4", raw_span="01012345678", masked_expected=True)
    items = [
        _b_item("B-1"),
        GoldenItem(id="P-1", module="C-5", domain="dasan", customer_utterance="번호는 01012345678", pii_patterns=[pii]),
    ]
    report = run_eval(items, Ports(retrieval=_OneDocRetrieval(), masking=_DigitsMasking(), generation=_SnippetGeneration()))
    assert report["domain_routing"] == NOT_IMPLEMENTED
    assert report["retrieval"] == {"recall_at_k": 1.0, "mrr": 1.0, "n": 1}
    assert report["no_answer"] == NO_SAMPLES
    assert report["trigger"] == NOT_IMPLEMENTED
    assert report["compliance"] == NOT_IMPLEMENTED
    assert report["call_guard"] == NOT_IMPLEMENTED
    assert report["masking"]["miss_count"] == 0 and report["masking"]["n"] == 1
    assert report["closure_gate"] == NOT_IMPLEMENTED
    assert report["call_temperature"] == NOT_IMPLEMENTED
