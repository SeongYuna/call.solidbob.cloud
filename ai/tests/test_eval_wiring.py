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

import pytest

from evaluation.golden_set import load_golden_set
from evaluation.harness import NO_SAMPLES, NOT_IMPLEMENTED, Ports, run_eval
from retrieval.adapter.outbound.es_bm25_retriever import EsBm25Retriever

GOLDEN_SET = Path(__file__).resolve().parents[2] / "golden-set" / "v1-50.json"


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
    # ⚠ 2026-08-28 단일 도메인 전환(`decisions/201`) — 다산에는 종결 처리 유형이 없어
    #   F-2 채점 케이스가 0건이다. 스포크는 꽂히지만 잴 것이 없다.
    #   **그 상태가 「미구현」과도 「통과」와도 다르게 보고되는지**를 여기서 고정한다.
    assert report["closure_gate"] == NO_SAMPLES, (
        f"F-2 가 '잴 것이 없음' 이 아닌 값으로 보고됐다: {report['closure_gate']!r}")


def test_절대_규칙은_건_단위로_보고된다():
    """[6.2절](/docs/06/) — 평균이 아니라 1건이라도 뚫리면 실패다.
    하네스가 그 판정을 내주는지(필드가 살아 있는지) 확인한다."""
    ports = _run_eval_module().build_ports(None, index="x")
    report = run_eval(load_golden_set(GOLDEN_SET), ports)

    assert report["masking"]["absolute_rule_passed"] is True, (
        f"C-5 누락 {report['masking']['miss_count']}건 — {report['masking']['missed_items']}")

    # F-2 도 같은 자리에서 본다. 지금은 케이스가 0건이라 **skip 으로 남긴다** —
    # `assert` 로 두면 스위트가 빨간불이라 다른 회귀를 못 보고, 조건을 지우면 0건인 채로
    # 초록불이 된다(장민석이 `test_golden_set_closure.py` 에서 고른 것과 같은 논리).
    # skip 은 "지금 이 절대 규칙을 안 재고 있다"를 **출력에 남긴다.**
    # 필요서류 체크리스트 케이스가 실리면 이 skip 이 저절로 사라지고 아래 단언이 살아난다.
    if report["closure_gate"] == NO_SAMPLES:
        pytest.skip("F-2 채점 케이스 0건 — 다산 단일 도메인 전환(decisions/201). "
                    "필요서류 체크리스트 케이스가 생기면 이 skip 이 사라진다")
    assert report["closure_gate"]["absolute_rule_passed"] is True, (
        f"F-2 오판정 — {report['closure_gate']['failed_items']}")
