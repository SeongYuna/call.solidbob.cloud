# Requirement: E-1, E-2, E-4, D-5, QUA-1
"""하네스 배선(wiring) 검증. 실제 검색/트리거/컴플라이언스/마스킹/게이트 스포크는 아직
없으므로, ①전부 미구현 상태에서 크래시 없이 "N/A"를 정직하게 보고하는지, ②hub 포트를
구현한 가짜 객체를 꽂았을 때 golden-set → metrics로 데이터가 올바르게 흘러가는지 두 가지만
확인한다. 실제 정확도 수치를 여기서 하드코딩하지 않는다 (6.2절 원칙 5)."""

from evaluation.golden_set import CallTemperatureGoldenCase, GoldenItem, PiiPattern, load_golden_set
from evaluation.harness import NO_SAMPLES, NOT_IMPLEMENTED, Ports, run_eval
from hub.app.dtos import (
    ClosureVerdict,
    DomainClassification,
    MaskedSpan,
    RetrievedDoc,
    TranscriptEvent,
    TriggerDecision,
    VoiceOutlier,
    VoiceOutlierVerdict,
)
from hub.app.ports.output import (
    ClosureGatePort,
    DomainRoutingPort,
    MaskingPort,
    RetrievalPort,
    TriggerPort,
    VoiceOutlierPort,
)


def test_all_ports_none_reports_not_implemented():
    items = load_golden_set()
    report = run_eval(items, Ports())
    for section in (
        "domain_routing", "retrieval", "trigger", "compliance", "masking", "closure_gate", "call_temperature",
        "no_answer",
    ):
        assert report[section] == "측정 불가 — 모듈 미구현"


class _EchoDomainRouting(DomainRoutingPort):
    """발화 안에 도메인 이름이 그대로 있으면 정답을 맞히는 가짜 포트 — 배선만 검증한다."""

    async def classify(self, utterance: str) -> DomainClassification:
        for domain in ("finance", "dasan", "shopping", "health"):
            if domain in utterance:
                return DomainClassification(domain=domain, confidence=1.0)
        return DomainClassification(domain="finance", confidence=0.0)  # 못 찾으면 임의 기본값


def test_도메인_라우팅은_더_이상_채점하지_않는다():
    """2026-08-28 단일 도메인 전환(`decisions/201`) — 도메인이 하나면 라우팅이 없다.

    허브 포트는 계약으로 남아 있지만 `ai/` 쪽 구현체를 지웠으므로 항상 "미구현"이다.
    골든셋의 `domain` 필드도 전부 `dasan` 이라 채점 대상 자체가 성립하지 않는다.
    """
    report = run_eval(load_golden_set(), Ports())
    assert report["domain_routing"] == NOT_IMPLEMENTED


class _PerfectClosureGate(ClosureGatePort):
    """골든셋의 기대값을 그대로 돌려주는 가짜 포트 구현 — 배선만 검증한다."""

    def evaluate(self, call_id, procedure, evidence, reason=None) -> ClosureVerdict:
        missing = tuple(field for field, ok in evidence.items() if not ok)
        return ClosureVerdict(
            call_id=call_id, procedure=procedure, evidence=evidence,
            verdict="complete" if not missing else "incomplete", missing=missing,
        )


def _without_f2(items):
    return [it for it in items if it.f2_case is None]


def test_F2_표본이_없으면_통과가_아니라_NO_SAMPLES_다():
    """스포크를 꽂아도 채점할 항목이 0건이면 **"통과"가 아니라 "잴 것이 없다"** 이고,
    그 둘을 구분해 보고하는지 확인한다(절대 원칙 10).

    ⚠ 2026-08-28: 이 단언이 원래 `result == NOT_IMPLEMENTED or result.get("n") == 0` 이었다.
    **docstring 이 약속한 「구분」을 실제로는 검증하지 않았고**, 그때 하네스는 빈 입력에
    `absolute_rule_passed: True` 를 내고 있었다 — 가짜 만점이 그대로 통과했다.
    이제 세 상태(미구현 / 표본 없음 / 채점됨)를 서로 다른 값으로 본다.

    2026-09-21 까지는 골든셋 전체가 F-2 0건이라 그대로 넣었다(`POLICY-1` 옛 판). `w5-f2-golden-cases` 로
    케이스가 생겨(`decisions/201`·`305`) **F-2 항목을 걸러낸 목록**으로 같은 것을 본다.
    """
    report = run_eval(_without_f2(load_golden_set()), Ports(closure_gate=_PerfectClosureGate()))
    assert report["closure_gate"] == NO_SAMPLES, report["closure_gate"]


def test_F2_표본이_있으면_건_단위로_채점된다():
    """배선만 본다 — 정확도 값은 규칙 스포크(`server/apps/closure_gate`)를 꽂는 하네스 실행이 낸다.
    `_PerfectClosureGate` 는 증거 키만 보는 가짜라 「키 없음 = false」 케이스에서 틀리는 것이 정상이고,
    그래서 여기서 `absolute_rule_passed` 를 단언하지 않는다(가짜 만점을 만들지 않는다)."""
    items = load_golden_set()
    n_f2 = sum(1 for it in items if it.f2_case is not None)
    assert n_f2 > 0
    report = run_eval(items, Ports(closure_gate=_PerfectClosureGate()))["closure_gate"]
    assert isinstance(report, dict), report
    assert report["n"] == n_f2
    assert set(report) == {"accuracy", "absolute_rule_passed", "failed_items", "n"}
    assert all(item_id.startswith("GS-") for item_id in report["failed_items"])


def test_스포크가_없는_것과_표본이_없는_것과_채점된_것을_구분한다():
    """셋 다 다음에 할 일이 다르다 — 만들 것인가, 골든셋을 채울 것인가, 결과를 읽을 것인가."""
    items = load_golden_set()
    no_spoke = run_eval(items, Ports())["closure_gate"]
    no_samples = run_eval(_without_f2(items), Ports(closure_gate=_PerfectClosureGate()))["closure_gate"]
    scored = run_eval(items, Ports(closure_gate=_PerfectClosureGate()))["closure_gate"]
    assert no_spoke == NOT_IMPLEMENTED
    assert no_samples == NO_SAMPLES
    assert no_spoke != no_samples
    assert isinstance(scored, dict) and scored not in (NOT_IMPLEMENTED, NO_SAMPLES)


class _FixedDelayTrigger(TriggerPort):
    """항상 발화 종료 900ms 뒤에 발동하는 가짜 포트 — 배선과 지연 분포 계산만 검증한다."""

    def decide(self, event: TranscriptEvent) -> TriggerDecision:
        return TriggerDecision(fire=True, at_ms=event.utterance_end_ms + 900)


def test_trigger_wiring_reports_latency_distribution():
    """⚠ 표본 수를 **골든셋에서 계산한다**(2026-09-09). 전에는 `== 6` 으로 박아 뒀는데,
    골든셋이 늘 때마다 여기가 깨지고 그때마다 숫자를 고치게 된다 — 그러면 이 테스트가
    「배선이 맞는가」가 아니라 「골든셋이 그대로인가」를 재는 것이 된다."""
    items = load_golden_set()
    expected_n = sum(1 for it in items if it.utterance_end_ms is not None)
    report = run_eval(items, Ports(trigger=_FixedDelayTrigger()))
    result = report["trigger"]
    assert expected_n > 0
    assert result["n"] == expected_n
    assert result["on_time_rate"] == 1.0  # 900ms는 0~1,500ms 허용 창 안
    assert result["latency_ms"]["p50"] == 900
    assert result["latency_ms"]["p95"] == 900
    assert result["latency_ms"]["n"] == expected_n
    assert result["not_fired"] == 0


class _DigitsOnlyMasking(MaskingPort):
    """연속 숫자 11자리(P4)만 가리는 가짜 — 절대 규칙이 '1건 누락 = 실패'로 뚫리는지 배선 검증."""

    def mask(self, text: str):
        idx = text.find("01012345678")
        if idx < 0:
            return text, ()
        return text[:idx] + "*" * 11 + text[idx + 11:], (MaskedSpan(type="P4", span=(idx, idx + 11)),)


def test_masking_wiring_reports_misses_per_pattern():
    items = load_golden_set()
    result = run_eval(items, Ports(masking=_DigitsOnlyMasking()))["masking"]
    # 숫자만 가리는 가짜 마스킹이라 P6(인명)·P7(상세주소)을 놓친다.
    # 2026-08-28 단일 도메인 전환으로 표본이 바뀌었다 — 항목 ID 를 하드코딩하지 않고
    # "숫자가 아닌 패턴은 전부 놓친다"는 성질로 검증한다. 골든셋이 늘어도 안 깨진다.
    assert result["absolute_rule_passed"] is False
    assert result["miss_count"] > 0
    non_digit = {p.pattern for it in items for p in it.pii_patterns if p.pattern in ("P6", "P7")}
    assert non_digit, "숫자가 아닌 PII 표본이 없어 이 테스트가 아무것도 검증하지 못한다"


class _HalfAddressMasking(MaskingPort):
    """주소 앞 어절만 가리고 번지를 남기는 가짜 — 2026-09-15 까지 하네스가 **통과로 셌던** 모양이다."""

    def mask(self, text: str):
        target = "성북구 정릉로"
        idx = text.find(target)
        if idx < 0:
            return text, ()
        return text[:idx] + "*" * len(target) + text[idx + len(target):], (MaskedSpan(type="P7", span=(idx, idx + len(target))),)


def test_partial_mask_leaving_house_number_is_a_miss():
    """`raw_span not in masked_text` 는 조각 하나만 가려져도 참이었다 — 번지가 보이는데 통과였다(GS-415)."""
    items = [
        GoldenItem(
            id="GS-T1", module="C-5", customer_utterance="성북구 정릉로 77길 12에서 물이 새요",
            pii_patterns=[PiiPattern(pattern="P7", raw_span="성북구 정릉로 77길 12", masked_expected=True)],
        )
    ]
    result = run_eval(items, Ports(masking=_HalfAddressMasking()))["masking"]
    assert result["miss_count"] == 1 and result["absolute_rule_passed"] is False


# ---------------------------------------------------------------------------
# D-5 통화 온도 — 2026-09-21 배선. 판정은 voice_signal 이 하고 여기서는 배선만 본다.
# ---------------------------------------------------------------------------


class _LoudByNameVoice(VoiceOutlierPort):
    """파일 이름에 `loud` 가 있는 발화를 튀었다고 하는 가짜 포트 — 오디오를 읽지 않는다. 배선만 검증한다."""

    async def judge(self, call_id, speaker, utterances) -> VoiceOutlierVerdict:
        return VoiceOutlierVerdict(
            call_id=call_id, speaker=speaker, judged=True,
            outliers=tuple(
                VoiceOutlier(segment_id=sid, speaker=speaker, robust_z=4.0, baseline_n=len(utterances))
                for sid, path in utterances if "loud" in path
            ),
        )


def _d5_item(item_id: str, names: list[str], expected: list[int], calm: list[int]) -> GoldenItem:
    return GoldenItem(
        id=item_id, module="D-5", domain="dasan",
        call_temperature=CallTemperatureGoldenCase(
            speaker="customer",
            utterances=[(i, f"/audio/{item_id}/{n}.wav") for i, n in enumerate(names)],
            expected_outliers=expected, calm=calm,
        ),
    )


def test_D5_포트가_없으면_미구현이다():
    assert run_eval(load_golden_set(), Ports())["call_temperature"] == NOT_IMPLEMENTED


def test_D5_포트를_꽂아도_음성_골든셋이_없어_표본_없음이다():
    """다산콜DB 는 발화 클립이라 통화 단위 기준선을 못 만든다(`w3-call-temperature`). 지금 정답은
    「측정 불가 — 골든셋에 채점 대상이 없다」이고, 이것을 「미구현」과 구분해 찍는 것이 배선의 목적이다
    (절대 원칙 10). 통화 단위 + 톤 라벨이 생기면 이 테스트는 바뀌어야 한다."""
    report = run_eval(load_golden_set(), Ports(voice_outlier=_LoudByNameVoice()))
    assert report["call_temperature"] == NO_SAMPLES, report["call_temperature"]
    assert report["call_temperature"] != NOT_IMPLEMENTED


def test_D5_케이스가_있으면_골든셋에서_채점기까지_흐른다():
    """손으로 만든 통화 2건 — 1건은 정답대로, 1건은 놓침 1 + 거짓 경고 1. 실제 정확도 수치가 아니다."""
    items = [
        # 통화 1: 발화 1 이 튀어야 하고 0·2 는 차분 — 가짜 포트가 정확히 맞힌다
        _d5_item("GS-D5-T1", ["calm", "loud", "calm"], expected=[1], calm=[0, 2]),
        # 통화 2: 발화 3 이 튀어야 하는데 조용한 파일이라 놓치고(fn), 차분한 발화 1 이 loud 라 거짓 경고(fp).
        #        발화 2 는 어느 라벨에도 없는 애매한 턴 — 튀었다고 해도 채점에 안 들어간다
        _d5_item("GS-D5-T2", ["calm", "loud", "loud", "quiet"], expected=[3], calm=[0, 1]),
    ]
    result = run_eval(items, Ports(voice_outlier=_LoudByNameVoice()))["call_temperature"]
    assert isinstance(result, dict), result
    assert result["n"] == 2
    assert (result["tp"], result["fn"], result["fp"]) == (1, 1, 1)
    assert result["recall"] == 0.5 and result["precision"] == 0.5
    assert result["calm_false_alarms"] == 1
    assert (result["judged_calls"], result["unjudged_calls"]) == (2, 0)


class _NeverJudgesVoice(VoiceOutlierPort):
    """기준선을 못 만든 것으로 돌려주는 가짜 — 「판정 안 함」이 0 점으로 새지 않는지 본다."""

    async def judge(self, call_id, speaker, utterances) -> VoiceOutlierVerdict:
        return VoiceOutlierVerdict(call_id=call_id, speaker=speaker, judged=False)


def test_D5_기준선을_못_만든_통화는_분모에서_빠진다():
    items = [_d5_item("GS-D5-T3", ["calm", "loud"], expected=[1], calm=[0])]
    result = run_eval(items, Ports(voice_outlier=_NeverJudgesVoice()))["call_temperature"]
    assert (result["judged_calls"], result["unjudged_calls"]) == (0, 1)
    assert result["recall"] is None and result["tp"] == 0 and result["fn"] == 0



class _ScoredRetrieval(RetrievalPort):
    """질의에 「여권」이 들어 있으면 빈 결과(= 「관련 문서 없음」)를, 아니면 점수가 질의 길이인 조항 하나를
    돌려주는 가짜 포트. 점수 눈금은 아무 의미가 없다 — 배선(기권 수·1순위 점수 요약)만 검증한다."""

    async def retrieve(self, utterance: str, top_k: int = 5) -> list[RetrievedDoc]:
        if "여권" in utterance:
            return []
        return [RetrievedDoc(doc_id="DASAN-TERM-4.4", title="전입신고", snippet="…", score=float(len(utterance)))]


def _b6_item(item_id: str, utterance: str) -> GoldenItem:
    return GoldenItem(id=item_id, module="B-6", domain="dasan", customer_utterance=utterance, expected_doc_ids=[])


def test_B6_포트가_없으면_미구현이다():
    assert run_eval(load_golden_set(), Ports())["no_answer"] == NOT_IMPLEMENTED


def test_B6_표본이_없으면_통과가_아니라_NO_SAMPLES_다():
    items = [it for it in load_golden_set() if it.module != "B-6"]
    report = run_eval(items, Ports(retrieval=_ScoredRetrieval()))
    assert report["no_answer"] == NO_SAMPLES, report["no_answer"]
    assert report["no_answer"] != NOT_IMPLEMENTED


def test_B6_케이스가_있으면_기권_수와_1순위_점수_요약을_센다():
    """정답 없음 3건 — 1건은 검색이 빈 결과(기권), 2건은 조항이 떴다(점수 = 질의 글자 수 2·7). 문턱은 여기서 판정하지 않는다."""
    items = [
        _b6_item("GS-B6-T1", "여권 재발급"),      # 기권
        _b6_item("GS-B6-T2", "로또"),             # 점수 2.0
        _b6_item("GS-B6-T3", "프로야구 경기"),     # 점수 7.0
    ]
    result = run_eval(items, Ports(retrieval=_ScoredRetrieval()))["no_answer"]
    assert isinstance(result, dict), result
    assert (result["n"], result["abstained"]) == (3, 1)
    assert (result["top1_score_min"], result["top1_score_median"], result["top1_score_max"]) == (2.0, 4.5, 7.0)


def test_B6_전부_기권하면_점수_요약은_측정_불가다():
    result = run_eval([_b6_item("GS-B6-T4", "여권 유효기간")], Ports(retrieval=_ScoredRetrieval()))["no_answer"]
    assert (result["n"], result["abstained"]) == (1, 1)
    assert "top1_score_min" not in result and result["top1_score"].startswith("측정 불가")


def test_B6_케이스는_B_검색_수치에_섞이지_않는다():
    """`hit_at_k` 는 정답이 빈 항목을 True 로 치므로, B-6 이 B 로 새면 Recall@5 가 부풀려진다.
    B 1건(오답) + B-6 2건을 같이 돌려도 검색 분모는 1 이고 Recall 은 0 이어야 한다."""
    items = [
        GoldenItem(id="GS-B-T1", module="B", domain="dasan", customer_utterance="수도요금 감면",
                   expected_doc_ids=["DASAN-TERM-3.6"]),
        _b6_item("GS-B6-T5", "로또"),
        _b6_item("GS-B6-T6", "여권"),
    ]
    report = run_eval(items, Ports(retrieval=_ScoredRetrieval()))
    assert report["retrieval"]["n"] == 1 and report["retrieval"]["recall_at_k"] == 0.0
    assert (report["no_answer"]["n"], report["no_answer"]["abstained"]) == (2, 1)
