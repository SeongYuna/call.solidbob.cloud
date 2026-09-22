# Requirement: E-1, QUA-1
"""`run_eval.py` 가 `eval_run.components` 에 적는 한 줄 — 실제로 꽂은 구성이다(w6-server-loose-ends ②)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _components():
    pytest.importorskip("elasticsearch")
    sys.path[:0] = [str(ROOT / "server"), str(ROOT / "server" / "apps"), str(ROOT / "ai" / "apps")]
    spec = importlib.util.spec_from_file_location("run_eval", ROOT / "scripts" / "run_eval.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.components_label


def test_검색기_NER_생성을_한_줄로_적는다():
    label = _components()
    assert label(retriever="hybrid", ner_enabled=True, generation_model=None) == "retriever=hybrid; masking=rule+ner; generation=none"
    assert label(retriever="bm25", ner_enabled=False, generation_model="exaone") == "retriever=bm25; masking=rule; generation=exaone"


def test_컬럼_길이에_들어간다():
    """db eval_run.components VARCHAR(100)."""
    assert len(_components()(retriever="rerank-dense", ner_enabled=True, generation_model="x" * 40)) <= 100
