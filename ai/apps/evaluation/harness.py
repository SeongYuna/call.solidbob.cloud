# Requirement: E-1, E-2, E-4
"""평가 하네스 골격 — [팀 분업 7.2절] 1주차엔 류준이 설계만 하고 이후 운영은 정성윤이
맡는다. 이 파일이 그 "설계"에 해당한다.

스포크(도메인 라우팅·검색·트리거·컴플라이언스·마스킹·F-2·C-6·D-5)의 접점은 **hub 아웃바운드 포트 하나뿐**이다
(apps/hub/app/ports/output/ — 2026-08-26 계약 이중화 해소). 스포크가 구현한 포트 객체를 `Ports(...)`에
꽂으면 골든셋으로 채점한다. 아직 구현이 없는 포트는 `None`으로 둬 "측정 불가 — 미구현"으로
정직하게 보고한다(목표 수치를 지어내지 않는다 — 6.2절 원칙 5).

채점 로직 자체(metrics/)는 완성돼 있고 apps/evaluation/tests/ 로 검증됐다. 이 파일은 포트 → metrics 배선만 한다.
async 포트(검색·컴플라이언스)는 여기서 `asyncio.run` 으로 돌린다 — 하네스는 스크립트이지 서버가 아니다.
"""

from __future__ import annotations

import asyncio
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Awaitable, TypeVar

from hub.app.dtos.transcript_dto import TranscriptEvent
from hub.app.ports.output.call_guard_port import CallGuardPort
from hub.app.ports.output.closure_gate_port import ClosureGatePort
from hub.app.ports.output.compliance_port import CompliancePort
from hub.app.ports.output.domain_routing_port import DomainRoutingPort
from hub.app.ports.output.masking_port import MaskingPort
from hub.app.ports.output.retrieval_port import RetrievalPort
from hub.app.ports.output.trigger_port import TriggerPort
from hub.app.ports.output.voice_outlier_port import VoiceOutlierPort

from .golden_set import GoldenItem, load_golden_set
from .metrics import call_guard as call_guard_metrics
from .metrics import call_temperature as call_temperature_metrics
from .metrics import closure_gate as closure_gate_metrics
from .metrics import compliance as compliance_metrics
from .metrics import domain_routing as domain_routing_metrics
from .metrics import latency as latency_metrics
from .metrics import masking as masking_metrics
from .metrics import masking_robustness
from .metrics import retrieval as retrieval_metrics
from .metrics import trigger as trigger_metrics

T = TypeVar("T")


def _run(coro: Awaitable[T]) -> T:
    return asyncio.run(coro)  # type: ignore[arg-type]


@dataclass
class Ports:
    """구현되지 않은 스포크는 None으로 둔다 — 해당 지표는 리포트에서 "미구현"으로 표시된다."""

    domain_routing: DomainRoutingPort | None = None
    retrieval: RetrievalPort | None = None
    trigger: TriggerPort | None = None
    compliance: CompliancePort | None = None
    masking: MaskingPort | None = None
    closure_gate: ClosureGatePort | None = None
    call_guard: CallGuardPort | None = None
    voice_outlier: VoiceOutlierPort | None = None  # D-5 통화 온도


NOT_IMPLEMENTED = "측정 불가 — 모듈 미구현"

# 스포크는 꽂혔는데 **골든셋에 채점 대상이 없는** 상태. `NOT_IMPLEMENTED` 와 구분한다 —
# 전자는 "만들지 않았다", 이쪽은 "만들었는데 잴 표본이 없다"이고 다음 할 일이 다르다.
#
# ⚠ 이 상수가 없으면 **표본 0건이 통과로 보고된다.** 채점기는 "틀린 게 없으면 통과"로
# 계산하므로(`len(failures) == 0`) 빈 입력에 `absolute_rule_passed: True` 를 낸다.
# 절대 규칙(C-5·F-2)에서 그건 가짜 만점이다 — 트리거를 일부러 안 꽂아 둔 것과 같은 이유다
# (절대 원칙 10). 장민석이 2026-08-27 에 `test_골든셋에_C5_케이스가_실려있다` 로 pytest
# 쪽에 세운 「빈 채로 초록불」 가드를, 2026-08-28 에 하네스 리포트 쪽에도 세웠다.
NO_SAMPLES = "측정 불가 — 골든셋에 채점 대상이 없다"


def retrieval_query(item: GoldenItem) -> str:
    """검색에 넣을 질의. **앞선 맥락이 있으면 함께 넣는다.**

    2026-09-09 골든셋 확장에서 필요해졌다. AI Hub 다산 실제 전사를 보면 서류 문의의
    상당수가 `"필요한 서류가 있나요?"` · `"어떤서류가 필요한가요?"` 처럼 **그 문장만으로는
    무엇을 묻는지 알 수 없는 중간 턴**이다. 발화만 질의로 쓰면 검색이 실패하는 것이
    당연해지고, 그러면 우리가 재는 것은 검색 성능이 아니라 「발화가 자족적인가」가 된다.

    ⚠ **맥락을 넣는 것이 점수를 올리려는 조치가 아니다.** `decisions/201` 이 B 를 「대화
    맥락으로 절차를 판정」이라고 정의한 그대로이고, 실제 시스템도 통화 앞부분을 갖고 있다.
    맥락 없는 항목은 이 함수가 발화 하나만 돌려주므로 동작이 달라지지 않는다.

    이어붙이는 순서는 **맥락 → 현재 발화**다. BM25 는 순서를 보지 않지만 dense·리랭커가
    붙으면 보게 되고, 사람이 읽는 순서와 같아야 디버깅할 때 헷갈리지 않는다.
    """
    parts = [*item.context_utterances, item.customer_utterance or ""]
    return " ".join(p for p in parts if p).strip()


def _event_from_item(item: GoldenItem) -> TranscriptEvent:
    """골든셋 항목을 트리거 포트가 받는 전사 이벤트로 바꾼다. 골든셋 발화는 이미 마스킹된 텍스트 취급."""
    return TranscriptEvent(
        call_id=item.id,
        segment_id=0,
        speaker="agent" if item.agent_utterance else "customer",
        text=item.agent_utterance or item.customer_utterance or "",
        is_final=True,
        utterance_end_ms=item.utterance_end_ms,
    )


def run_eval(items: list[GoldenItem], ports: Ports) -> dict:
    report: dict = {}

    # B-0: 도메인 라우팅 (자동 분류) — 정답 도메인이 있고 분류할 발화 텍스트가 있는 항목만 채점
    # B-0 은 **통화 초반 고객 발화로 도메인을 판정**하는 것이다(`decisions/007`).
    # 그래서 B(검색) 항목만 채점한다 — C·C-5 항목의 발화는 마스킹·컴플라이언스 시나리오라
    # 도메인 단서가 **아예 없다**("본인 확인을 위해서 주민등록번호를 불러주시겠어요?" 가
    # 어느 도메인인지 텍스트만 보고는 알 수 없다. 그 항목의 domain 은 "어느 시나리오에
    # 속하는가"를 적은 메타데이터이지 발화에서 추론할 대상이 아니다).
    #
    # 2026-08-27 실측으로 발견했다. 34건 전체로 재면 검색 v1 0.647 / 분류기 0.588 인데,
    # B 14건만 보면 0.857 / 0.786 이다 — 나머지 20건에서 둘 다 0.45~0.50(사실상 찍기)이라
    # **측정할 수 없는 것을 섞어 재고 있었다**(절대 원칙 10).
    domain_items = [
        it for it in items if it.module == "B" and it.domain is not None and it.customer_utterance
    ]
    if ports.domain_routing is None:
        report["domain_routing"] = NOT_IMPLEMENTED
    else:
        expected_domains = [it.domain for it in domain_items]
        predicted_domains = [
            _run(ports.domain_routing.classify(it.customer_utterance or it.agent_utterance or "")).domain
            for it in domain_items
        ]
        report["domain_routing"] = domain_routing_metrics.score_domain_routing(
            expected_domains, predicted_domains
        )

    # B: 검색 (Recall@5, MRR)
    b_items = [it for it in items if it.module == "B"]
    if ports.retrieval is None:
        report["retrieval"] = NOT_IMPLEMENTED
    else:
        pairs = []
        for it in b_items:
            docs = _run(ports.retrieval.retrieve(retrieval_query(it), top_k=5))
            pairs.append((it.expected_doc_ids, [d.doc_id for d in docs]))
        report["retrieval"] = retrieval_metrics.aggregate_recall_mrr(pairs)

    # B-6: 「관련 문서 없음」 — 지식베이스에 정답이 없는 문의(`module: "B-6"`, `expected_doc_ids: []`).
    # B 항목과 **섞지 않는다** — `hit_at_k` 는 정답이 빈 항목을 True 로 치고 `aggregate_recall_mrr` 은
    # 분모에서 빼므로, B 로 넣으면 96건 수치가 흔들리거나 부풀려진다(6주차 판정 직전, `decisions/123` 과
    # 같은 이유). 여기서는 판정하지 않고 두 가지만 센다 — ① 검색이 빈 결과를 돌려줘 「관련 문서 없음」으로
    # 넘어간 건수(`abstained`) ② 1순위 점수 분포(min/median/max — BM25 raw · 코사인 · 리랭커 로짓 등
    # 구성마다 눈금이 다르므로 구성 간 비교는 하지 않는다).
    # ⚠ 2026-09-21 현재 검색에 점수 문턱이 없어 `abstained` 가 0 으로 나오는 것이 **정직한 값**이다 —
    # 문턱 값은 `scripts/measure_no_answer_threshold.py` 의 분포 측정으로 팀이 정한다
    # (`w5-b6-no-answer-threshold`). 문턱이 생기면 이 항목이 코드 변경 없이 그 효과를 찍는다.
    b6_items = [it for it in items if it.module == "B-6"]
    if ports.retrieval is None:
        report["no_answer"] = NOT_IMPLEMENTED
    elif not b6_items:
        report["no_answer"] = NO_SAMPLES
    else:
        top1_scores: list[float] = []
        abstained = 0
        for it in b6_items:
            docs = _run(ports.retrieval.retrieve(retrieval_query(it), top_k=5))
            if not docs:
                abstained += 1
                continue
            top1_scores.append(docs[0].score)
        no_answer: dict = {"n": len(b6_items), "abstained": abstained}
        if top1_scores:
            no_answer["top1_score_min"] = min(top1_scores)
            no_answer["top1_score_median"] = statistics.median(top1_scores)
            no_answer["top1_score_max"] = max(top1_scores)
        else:
            no_answer["top1_score"] = "측정 불가 — 검색이 전부 기권해 점수가 없다"
        report["no_answer"] = no_answer

    # B-1: 트리거 (utterance_end_ms 가 있는 항목만 채점 가능)
    # 허용 창(0~1,500ms)은 합/불 판정선일 뿐이므로, 판정 결과와 별개로 발동
    # 지연시간(delta = at_ms - utterance_end_ms) 분포를 p50/p95로 함께 낸다
    # ([핵심 기술 난제 4.1절], [평가 설계 6.1절] — 2026-08-25 팀 컨펌).
    if ports.trigger is None:
        report["trigger"] = NOT_IMPLEMENTED
    else:
        labels = []
        deltas: list[float] = []
        missed = 0
        for it in items:
            if it.utterance_end_ms is None:
                continue
            decision = ports.trigger.decide(_event_from_item(it))
            if not decision.fire or decision.at_ms is None:
                missed += 1  # 발동 자체가 안 됨 — 지연 분포에는 넣지 않고 따로 센다
                continue
            deltas.append(decision.at_ms - it.utterance_end_ms)
            labels.append(trigger_metrics.classify_trigger(it.utterance_end_ms, decision.at_ms))
        result = trigger_metrics.aggregate_trigger(labels)
        result["latency_ms"] = latency_metrics.summarize_latency(deltas)
        result["not_fired"] = missed
        report["trigger"] = result

    # C-1~C-4: 컴플라이언스 (재현율/정밀도)
    c_items = [it for it in items if it.module in ("C-1", "C-2", "C-3", "C-4")]
    if ports.compliance is None:
        report["compliance"] = NOT_IMPLEMENTED
    else:
        expected = [it.compliance_violation is not None for it in c_items]
        predicted = [
            bool(_run(ports.compliance.detect(it.agent_utterance or it.customer_utterance or "")))
            for it in c_items
        ]
        report["compliance"] = compliance_metrics.score_binary_predictions(expected, predicted)

    # C-6: 콜 가드 — **고객** 폭언·위기 신호. C-1~C-4 와 화자가 반대라 항목도 따로 고른다.
    # 정상 발화(위반 아님)도 채점 대상이다 — 재현율만 보면 "전부 폭언"이라고 답하는
    # 구현이 만점을 받는다(절대 원칙 10).
    c6_items = [it for it in items if it.module == "C-6"]
    if ports.call_guard is None:
        report["call_guard"] = NOT_IMPLEMENTED
    elif not c6_items:
        report["call_guard"] = NO_SAMPLES
    else:
        predictions = []
        for it in c6_items:
            flags = _run(ports.call_guard.detect(it.customer_utterance or ""))
            # 여러 건이 잡히면 첫 번째를 대표로 본다. 갈래가 섞여 잡히면 위기(distress)를
            # 우선한다 — 5.4 조가 그쪽 대응을 다르게 정하므로, 놓치는 쪽이 더 위험하다.
            predicted = None
            if flags:
                distress = next((f for f in flags if f.category == "distress"), None)
                predicted = (distress or flags[0]).category
            predictions.append(
                call_guard_metrics.CallGuardPrediction(
                    item_id=it.id,
                    expected_type=it.call_guard.type if it.call_guard else None,
                    predicted_type=predicted,
                )
            )
        report["call_guard"] = call_guard_metrics.score_call_guard(predictions)

    # C-5: 마스킹 (절대 규칙)
    if ports.masking is None:
        report["masking"] = NOT_IMPLEMENTED
    else:
        cases = []
        for it in items:
            if not it.pii_patterns:
                continue
            masked_text, spans = ports.masking.mask(it.customer_utterance or "")
            predicted_patterns = {s.type for s in spans}
            for pii in it.pii_patterns:
                pattern_matched = pii.pattern in predicted_patterns
                # 「가려졌는가」는 **개인정보가 결과에 읽을 수 있게 남았는지**로 본다. 패턴 이름이
                # 달라도 값이 사라졌으면 노출은 없었다 — 절대 규칙이 지키려는 것은 그쪽이다.
                # `raw_span` 이 비어 있는 항목(음성 케이스·문맥 한계 케이스)은 가릴 글자를
                # 특정하지 않은 것이므로 예전처럼 패턴 등장 여부로 본다.
                #
                # ⚠ 2026-09-15 까지는 `raw_span not in masked_text` 였다 — **조각 하나만 가려져도 통과**였다.
                #   `"성북구 정릉로 77길 12"` 를 규칙이 `"******* 77길 12"` 로 가려 **번지가 그대로 보이는데**
                #   통과로 셌다(GS-415, 오류 내성 곡선을 재다 발견). 부분 마스킹이 절대 규칙을 가짜로 통과시키는
                #   구조라 `masking_robustness.survives`(번호 연속 4자리 · 이름 2글자 · 주소 3글자)로 바꿨다.
                was_masked = (
                    not masking_robustness.survives(pii.pattern, pii.raw_span, masked_text)
                    if pii.raw_span
                    else pattern_matched
                )
                cases.append(
                    masking_metrics.MaskingCase(
                        item_id=it.id,
                        pattern=pii.pattern,
                        should_be_masked=pii.masked_expected,
                        was_masked=was_masked,
                        pattern_matched=pattern_matched,
                    )
                )
        # 마스킹도 같다 — 표본이 0건이면 「누락 0건 통과」가 아니라 「잴 것이 없다」다.
        report["masking"] = masking_metrics.score_masking(cases) if cases else NO_SAMPLES

    # F-2: 종결 게이트 (절대 규칙)
    f2_items = [it for it in items if it.f2_case is not None]
    if ports.closure_gate is None:
        report["closure_gate"] = NOT_IMPLEMENTED
    elif not f2_items:
        # 2026-08-28 다산 단일 도메인 전환(`decisions/201`)으로 종결 케이스가 0건이 됐다.
        # 여기서 채점기를 부르면 `absolute_rule_passed: True` 가 나온다 — **통과가 아니라
        # 잴 것이 없는 것**이므로 구분해서 보고한다. 필요서류 체크리스트 케이스가 생기면
        # 이 분기를 타지 않게 되고, 그때 F-2 는 다시 진짜로 채점된다.
        report["closure_gate"] = NO_SAMPLES
    else:
        predictions = []
        for it in f2_items:
            case = it.f2_case
            verdict = ports.closure_gate.evaluate(
                call_id=it.id, procedure=case.procedure, evidence=case.evidence
            )
            predictions.append(
                closure_gate_metrics.F2Prediction(
                    item_id=it.id,
                    expected_verdict=case.expected_verdict,
                    predicted_verdict=verdict.verdict,
                    expected_missing=case.expected_missing,
                    predicted_missing=list(verdict.missing),
                )
            )
        report["closure_gate"] = closure_gate_metrics.score_closure_gate(predictions)

    # D-5: 통화 온도 — 화자 자신의 기준선 대비 튄 발화(`decisions/203`). 판정은 `voice_signal`(규칙)이
    # 하고 여기서는 라벨과 대조만 한다. 항목은 `call_temperature` 필드가 있는 것만 — 통화 1건·화자 1명이
    # 케이스 1건이다.
    #
    # ⚠ 2026-09-21 배선 시점에 **음성 골든셋이 0건이다**(다산콜DB 는 발화 클립이라 통화 단위 기준선을
    # 못 만든다, `w3-call-temperature`). 그래서 포트를 꽂아도 `NO_SAMPLES` 가 나오는 것이 정답이고,
    # 「미구현」과 「표본 없음」을 갈라 찍는 것이 이 배선의 목적이다(절대 원칙 10). 통화 단위 + 톤
    # 라벨이 생기면 이 분기를 타지 않게 되고 코드 변경 없이 채점된다.
    d5_items = [it for it in items if it.call_temperature is not None]
    if ports.voice_outlier is None:
        report["call_temperature"] = NOT_IMPLEMENTED
    elif not d5_items:
        report["call_temperature"] = NO_SAMPLES
    else:
        cases = []
        for it in d5_items:
            gold = it.call_temperature
            verdict = _run(
                ports.voice_outlier.judge(call_id=it.id, speaker=gold.speaker, utterances=gold.utterances)
            )
            cases.append(
                call_temperature_metrics.CallTemperatureCase(
                    call_id=it.id,
                    expected_outliers=frozenset(gold.expected_outliers),
                    calm=frozenset(gold.calm),
                    predicted_outliers=frozenset(o.segment_id for o in verdict.outliers),
                    # 기준선을 못 만든 통화는 0 이 아니라 「판정하지 않음」으로 센다 — 채점기가 분모에서 뺀다
                    judged=verdict.judged,
                )
            )
        result = {"n": len(cases)}
        result.update(asdict(call_temperature_metrics.score(cases)))
        report["call_temperature"] = result

    return report


def main() -> None:  # pragma: no cover — 수동 실행용
    from .report import print_report

    items = load_golden_set()
    report = run_eval(items, Ports())  # 전부 미구현 상태로 골격만 확인
    print_report(report, golden_set_path=Path(__file__).resolve().parents[3] / "golden-set" / "v1-150.json")


if __name__ == "__main__":  # pragma: no cover
    main()
