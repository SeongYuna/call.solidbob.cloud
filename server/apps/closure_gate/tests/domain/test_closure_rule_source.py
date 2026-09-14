# Requirement: F-2, QUA-1
"""규칙표가 **조항 원문과 같은가** — 옮겨 적다 틀리면 F-2 절대 규칙이 조용히 어긋난다.

`knowledge-base/dasan/terms/TERM.md` 의 필요서류 조항을 읽어, 규칙표의 절차·서류 이름이 그 조항 본문에 실제로
있는지 대조한다. **규칙이 옳은지는 보지 않는다** — 원문에 없는 서류를 지어내지 않았는지만 본다.
"""

import re
from pathlib import Path

import pytest

from closure_gate.domain.value_objects.closure_rule import EXCLUDED, RULES

TERM = Path(__file__).resolve().parents[5] / "knowledge-base" / "dasan" / "terms" / "TERM.md"


def _sections() -> dict[str, str]:
    text = TERM.read_text(encoding="utf-8")
    parts = re.split(r"<!-- id: (DASAN-TERM-[\d.]+) -->", text)
    return {parts[i]: parts[i + 1].split("\n## ")[0] for i in range(1, len(parts) - 1, 2)}


def _squash(s: str) -> str:
    return re.sub(r"[\s*()]", "", s)


SECTIONS = _sections() if TERM.exists() else {}


def test_지식베이스를_찾았다():
    assert SECTIONS, f"TERM.md 를 못 읽었다: {TERM}"


@pytest.mark.parametrize("procedure", list(RULES))
def test_절차는_필요서류_조항이다(procedure):
    assert procedure in SECTIONS, f"{procedure} 조항이 지식베이스에 없다"
    assert "서류" in SECTIONS[procedure].split("\n", 2)[1], f"{procedure} 제목이 필요서류 조항이 아니다"


@pytest.mark.parametrize("procedure, name", [(p, d.name) for p, r in RULES.items() for d in r.required])
def test_필수_서류_이름이_조항_본문에_있다(procedure, name):
    body = _squash(SECTIONS[procedure])
    # 「A 또는 B」 는 원문에서 한 덩어리로 붙어 있지 않을 수 있어 조각마다 본다
    for piece in re.split(r"또는", name):
        assert _squash(piece) in body, f"{procedure}: '{piece}' 가 조항 본문에 없다"


def test_필요서류_조항은_전부_규칙이거나_제외_목록에_있다():
    """새 필요서류 조항이 생겼는데 규칙도 제외 사유도 없으면, 그 절차는 조용히 422 가 된다."""
    titled = {sid for sid, body in SECTIONS.items() if "서류" in body.split("\n", 2)[1]}
    assert titled - set(RULES) - set(EXCLUDED) == set()
