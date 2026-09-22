# Requirement: E-1, B-2
"""합성 루트 테스트 — 스포크를 hub 포트에 꽂는 배선만 본다 (`scripts/run_eval.py` 소관).

**여기가 `apps/` 밖인 이유**: `.importlinter` 의 module-independence 계약이
`evaluation` ↔ `retrieval` 직접 참조를 막는다. 두 모듈의 접점은 hub 포트(추상)뿐이고,
구체 구현을 꽂는 일은 두 모듈 **밖에서** 해야 한다. 그 배선을 검증하는 테스트도 밖에 둔다 —
`server/tests/` 가 `main.py` 에 대해 하는 역할과 같다.

ES 없이 돈다. 가짜 클라이언트로 하네스가 실제로 숫자를 내는지만 확인한다.
"""

from __future__ import annotations

from pathlib import Path

from evaluation.golden_set import load_golden_set
from evaluation.harness import NO_SAMPLES, NOT_IMPLEMENTED, Ports, run_eval
from retrieval.adapter.outbound.es_bm25_retriever import EsBm25Retriever

# 공식 골든셋(`ai/CLAUDE.md` §5). 2026-09-22 까지 옛 `v1-50.json`(13건)을 읽어 F-2 검사가 늘 skip 이었고
# C-5 절대 규칙도 6건만 봤다(`w6-test-hygiene-eval-wiring`). ⚠ 이 파일은 계속 자란다 — 표본 수를
# 여기 적지 않는다. 단언은 «채점됐는가(n > 0)» 와 «절대 규칙이 뚫리지 않았는가» 로만 한다.
GOLDEN_SET = Path(__file__).resolve().parents[2] / "golden-set" / "v1-150.json"


class StubClient:
    """항상 첫 정답 문서를 1위로 돌려주는 ES 대역. 하네스 배선만 보는 것이라 이걸로 충분하다."""

    def __init__(self, doc_id: str):
        self._doc_id = doc_id

    def search(self, **kwargs):
        return {
            "hits": {
                "hits": [
                    {
                        "_id": self._doc_id,
                        "_score": 1.0,
                        "_source": {"doc_id": self._doc_id, "title": "제목", "text": "본문"},
                    }
                ]
            }
        }


def test_포트를_꽂지_않으면_미구현으로_보고한다():
    """목표 수치를 지어내지 않는다 — 절대 원칙 2를 하네스가 지키는지 본다."""
    report = run_eval(load_golden_set(GOLDEN_SET), Ports())
    assert report["retrieval"] == NOT_IMPLEMENTED


def test_검색을_꽂으면_Recall과_MRR이_나온다():
    """w2-naive-rag 의 완료 조건 — Ports(retrieval=...) 에 꽂으면 숫자가 나온다."""
    items = load_golden_set(GOLDEN_SET)
    answer = next(it.expected_doc_ids[0] for it in items if it.expected_doc_ids)

    report = run_eval(items, Ports(retrieval=EsBm25Retriever(StubClient(answer))))

    assert isinstance(report["retrieval"], dict), "검색이 '미구현'으로 보고됐다"
    result = report["retrieval"]
    assert result["n"] > 0, "채점된 항목이 없다"
    assert 0.0 <= result["recall_at_k"] <= 1.0
    assert 0.0 <= result["mrr"] <= 1.0
    # 그 한 건은 1위로 맞혔으므로 0 보다 커야 한다 — 배선이 끊겨 있으면 0 이 나온다
    assert result["recall_at_k"] > 0


def test_채점_단위는_chunk_id_가_아니라_doc_id_다():
    """조항이 쪼개져 `_id` 에 `#1` 이 붙어도 골든셋과 대조되는 값은 조항 ID 여야 한다."""
    items = load_golden_set(GOLDEN_SET)
    answer = next(it.expected_doc_ids[0] for it in items if it.expected_doc_ids)

    class SplitChunkClient(StubClient):
        def search(self, **kwargs):
            resp = super().search(**kwargs)
            resp["hits"]["hits"][0]["_id"] = f"{self._doc_id}#1"  # 청크는 쪼개졌지만
            return resp                                            # doc_id 는 그대로다

    report = run_eval(items, Ports(retrieval=EsBm25Retriever(SplitChunkClient(answer))))
    assert report["retrieval"]["recall_at_k"] > 0


# ── C-5 마스킹 · F-2 게이트 배선 (2026-08-27 추가) ───────────────────────────
#
# 두 스포크는 `server/apps/` 에 산다. 규칙 기반 판정이라 요청 경로에서 매번 실행되기
# 때문이다(`server/CLAUDE.md` §0). `scripts/run_eval.py` 가 두 모듈 밖의 합성 루트라
# 거기서 꽂는다 — 의존 방향(ai → server)에도, 모듈 상호 독립 계약에도 걸리지 않는다.

import importlib.util  # noqa: E402

RUN_EVAL = Path(__file__).resolve().parents[2] / "scripts" / "run_eval.py"


def _run_eval_module():
    """`scripts/run_eval.py` 를 파일 경로로 불러온다 — 패키지가 아니라 스크립트다."""
    spec = importlib.util.spec_from_file_location("run_eval", RUN_EVAL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_합성_루트가_마스킹과_F2를_꽂는다():
    """배선이 끊기면 하네스가 다시 「측정 불가」로 돌아간다 — 그 회귀를 여기서 잡는다."""
    ports = _run_eval_module().build_ports(None, index="x")   # ES 없이
    assert ports.masking is not None, "C-5 마스킹이 꽂히지 않았다"
    assert ports.closure_gate is not None, "F-2 게이트가 꽂히지 않았다"


def test_ES가_없어도_마스킹과_F2는_채점된다():
    """둘 다 외부 의존이 없는 순수 규칙이다 — ES 가 꺼져 있어도 숫자가 나와야 한다.
    검색만 「측정 불가」로 남는 것이 정상이다."""
    ports = _run_eval_module().build_ports(None, index="x")
    report = run_eval(load_golden_set(GOLDEN_SET), ports)

    assert report["retrieval"] == NOT_IMPLEMENTED          # ES 가 없으니 당연하다
    assert isinstance(report["masking"], dict), "마스킹이 '미구현'으로 보고됐다"
    assert report["masking"]["n"] > 0
    # 2026-09-21 필요서류 체크리스트 케이스(`w5-f2-golden-cases`)가 실려 F-2 도 채점된다.
    # 2026-08-28~09-21 에는 0건이라 여기서 `NO_SAMPLES` 를 단언했다 — 그 성질은 아래 테스트가 이어받는다.
    assert isinstance(report["closure_gate"], dict), (
        f"F-2 가 채점되지 않았다: {report['closure_gate']!r}")
    assert report["closure_gate"]["n"] > 0


def test_F2_케이스가_없으면_미구현도_통과도_아닌_잴것없음이다():
    """스포크는 꽂혔는데 잴 것이 없는 상태가 「미구현」과도 「통과」와도 다르게 보고되는지 고정한다.

    2026-08-28 단일 도메인 전환(`decisions/201`) 뒤 실제로 이 상태였다 — 채점기를 빈 입력으로
    부르면 `absolute_rule_passed: True` 가 나와 «0건 통과» 가 됐을 것이다(절대 원칙 5).
    지금 골든셋에는 F-2 케이스가 있으므로 **F-2 항목을 뺀 부분집합**으로 그 경로를 연다.
    """
    items = [it for it in load_golden_set(GOLDEN_SET) if it.f2_case is None]
    assert items, "F-2 가 아닌 항목이 없다 — 골든셋이 비었다"
    report = run_eval(items, _run_eval_module().build_ports(None, index="x"))
    assert report["closure_gate"] == NO_SAMPLES, (
        f"F-2 가 '잴 것이 없음' 이 아닌 값으로 보고됐다: {report['closure_gate']!r}")


def test_절대_규칙은_건_단위로_보고된다():
    """[6.2절](/docs/06/) — 평균이 아니라 1건이라도 뚫리면 실패다.
    하네스가 그 판정을 내주는지(필드가 살아 있는지), 그리고 지금 골든셋에서 뚫리지 않았는지 본다."""
    ports = _run_eval_module().build_ports(None, index="x")
    report = run_eval(load_golden_set(GOLDEN_SET), ports)

    masking = report["masking"]
    assert masking["n"] > 0, "C-5 채점 표본이 0건이다 — 통과가 아니라 측정 불가다"
    assert masking["absolute_rule_passed"] is True, (
        f"C-5 누락 {masking['miss_count']}건 — {masking['missed_items']}")
    assert masking["miss_count"] == 0

    # F-2 도 같은 자리에서 본다. 2026-09-22 까지 여기가 **늘 skip** 이었다 — 옛 `v1-50` 을 읽어
    # 케이스가 0건으로 보였기 때문이다(실제로는 `v1-150` 에 99건이 채점·통과 중이었다).
    # skip 을 걷어낸다: 케이스가 사라지면 `isinstance` 단언이 실패로 알려 준다(«0건 통과» 를 막는다).
    gate = report["closure_gate"]
    assert isinstance(gate, dict), f"F-2 가 채점되지 않았다: {gate!r}"
    assert gate["n"] > 0
    assert gate["absolute_rule_passed"] is True, f"F-2 오판정 — {gate['failed_items']}"
    assert gate["accuracy"] == 1.0
