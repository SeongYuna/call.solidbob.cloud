# Requirement: E-1, E-2, E-4
"""평가 하네스 골격 — [팀 분업 7.2절] 1주차엔 류준이 설계만 하고 이후 운영은 정성윤이
맡는다. 이 파일이 그 "설계"에 해당한다.

스포크(도메인 라우팅·검색·트리거·컴플라이언스·마스킹·F-2)의 접점은 **hub 아웃바운드 포트 하나뿐**이다
(apps/hub/app/ports/output/ — 2026-08-26 계약 이중화 해소). 스포크가 구현한 포트 객체를 `Ports(...)`에
꽂으면 골든셋으로 채점한다. 아직 구현이 없는 포트는 `None`으로 둬 "측정 불가 — 미구현"으로
정직하게 보고한다(목표 수치를 지어내지 않는다 — 6.2절 원칙 5).

채점 로직 자체(metrics/)는 완성돼 있고 apps/evaluation/tests/ 로 검증됐다. 이 파일은 포트 → metrics 배선만 한다.
async 포트(검색·컴플라이언스)는 여기서 `asyncio.run` 으로 돌린다 — 하네스는 스크립트이지 서버가 아니다.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, TypeVar

from hub.app.dtos.transcript_dto import TranscriptEvent
from hub.app.ports.output.closure_gate_port import ClosureGatePort
from hub.app.ports.output.compliance_port import CompliancePort
from hub.app.ports.output.domain_routing_port import DomainRoutingPort
from hub.app.ports.output.masking_port import MaskingPort
from hub.app.ports.output.retrieval_port import RetrievalPort
from hub.app.ports.output.trigger_port import TriggerPort

from .golden_set import GoldenItem, load_golden_set
from .metrics import closure_gate as closure_gate_metrics
from .metrics import compliance as compliance_metrics
from .metrics import domain_routing as domain_routing_metrics
from .metrics import latency as latency_metrics
from .metrics import masking as masking_metrics
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
            docs = _run(ports.retrieval.retrieve(it.customer_utterance or "", top_k=5))
            pairs.append((it.expected_doc_ids, [d.doc_id for d in docs]))
        report["retrieval"] = retrieval_metrics.aggregate_recall_mrr(pairs)

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

    # C-5: 마스킹 (절대 규칙)
    if ports.masking is None:
        report["masking"] = NOT_IMPLEMENTED
    else:
        cases = []
        for it in items:
            if not it.pii_patterns:
                continue
            _, spans = ports.masking.mask(it.customer_utterance or "")
            predicted_patterns = {s.type for s in spans}
            for pii in it.pii_patterns:
                cases.append(
                    masking_metrics.MaskingCase(
                        item_id=it.id,
                        pattern=pii.pattern,
                        should_be_masked=pii.masked_expected,
                        was_masked=pii.pattern in predicted_patterns,
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
                call_id=it.id, closure_type=case.closure_type, evidence=case.evidence
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

    return report


def main() -> None:  # pragma: no cover — 수동 실행용
    from .report import print_report

    items = load_golden_set()
    report = run_eval(items, Ports())  # 전부 미구현 상태로 골격만 확인
    print_report(report, golden_set_path=Path(__file__).resolve().parents[3] / "golden-set" / "v1-10.json")


if __name__ == "__main__":  # pragma: no cover
    main()
