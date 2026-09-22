# Requirement: B-2, B-3, B-4, C-5
"""의존 방향 `ai → server` 한쪽 — **`server/` 는 모델 HTTP 표면을 import 하지 않는다**(`decisions/213`).

fastapi 없이 도는 검사다 — CI `ai` job 에서 실제로 돈다. `server/.importlinter` 계약 2 의 금지 목록에
`model_serving` 이 없어서(2026-09-22, 그 파일은 이번 작업 범위 밖) 그 몫을 여기서 한다.
`ai/.importlinter` 로 못 거는 이유: `hub` 등을 root_packages 에 올리면 `evaluation → hub.dtos → pydantic`
같은 간접 경로가 계약 3 에 새로 잡힌다 — 이 검사 하나 때문에 기존 계약의 뜻이 바뀐다.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FORBIDDEN = {"model_serving", "model_server"}


def test_server_는_모델_표면을_import_하지_않는다():
    """서버는 모델 표면에 **HTTP 로만** 닿는다. `server/main.py`(합성 루트)도 예외가 아니다."""
    hits = []
    for py in (REPO / "server").rglob("*.py"):
        if ".venv" in py.parts or "node_modules" in py.parts:
            continue
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module]
            hits += [f"{py.relative_to(REPO)}:{node.lineno} {n}" for n in names if n.split(".")[0] in FORBIDDEN]
    assert hits == []
