# Requirement: C-5, E-3
"""오류가 섞인 전사에서 C-5 누락을 세는 규칙 (`w5-masking-recall-curve`).

하네스의 C-5 채점(`harness.py`)은 «골든셋 `raw_span` 이 결과에 **그대로** 남았는가» 로 본다. 깨끗한 입력에서는 맞는
기준이지만 **STT 오류를 넣으면 가짜 통과가 난다** — `01012345678` 이 `공일공 1234 5678` 로 바뀌면 원문 조각은 결과에
없지만 번호는 그대로 노출돼 있다. 그래서 «살아남았는가» 를 따로 정한다.

    입력(주입본)에 살아있다 ─┬─ 결과(마스킹본)에도 살아있다 → **누락**
                            └─ 결과에서 사라졌다          → 가려짐
    입력(주입본)에서 이미 사라졌다                         → **소거** — 주입이 지웠다. 분모에서 빼고 따로 센다

«살아남음» 기준 — **애매하면 살아있다고 본다**(누락 0건 > 과잉 억제, 절대 원칙 3):

| 패턴 | 살아남음 |
|---|---|
| P1~P5 (번호) | 원래 숫자열과 **연속 4자리 이상**(4자리보다 짧으면 전부) 겹치는 숫자 덩어리가 있다. 한글 숫자 읽기(`공일공`)는 숫자로 되돌려 본다. 공백·하이픈은 이어 붙인다 |
| P6 (인명) | 공백을 뺀 이름과 **연속 2글자 이상** 겹친다 — 성+이름 첫 글자만 보여도 노출이다 |
| P7 (주소) | 공백을 뺀 주소와 **연속 3글자 이상** 겹친다 — 번지만 가리고 도로명(`정릉로`)을 남겨도 노출이다 |

순수 파이썬이다(`ai/.importlinter` 계약 3 — 채점에 모델을 쓰지 않는다, 절대 원칙 1).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_SINO = {"공": "0", "영": "0", "일": "1", "이": "2", "삼": "3", "사": "4", "오": "5", "육": "6", "칠": "7", "팔": "8", "구": "9"}
# 한글 숫자 읽기는 **3글자 이상 이어질 때만** 숫자로 본다 — `"이"`·`"오"` 한 글자는 조사·말끝이 훨씬 흔하다.
_SINO_RUN = re.compile(r"[공영일이삼사오육칠팔구](?:\s?[공영일이삼사오육칠팔구]){2,}")
_NUMERIC = frozenset({"P1", "P2", "P3", "P4", "P5"})
_MIN_OVERLAP = {"P6": 2, "P7": 3}


def _longest_common_substring(a: str, b: str) -> int:
    if not a or not b:
        return 0
    best = 0
    prev = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                best = max(best, cur[j])
        prev = cur
    return best


def _digit_runs(text: str) -> list[str]:
    text = _SINO_RUN.sub(lambda m: "".join(_SINO[c] for c in m.group(0) if c in _SINO), text)
    # 숫자 사이의 공백·하이픈은 구분자로 보고 이어 붙인다(STT 가 끊어 쓴 번호도 번호다)
    joined = re.sub(r"(?<=\d)[\s\-.]+(?=\d)", "", text)
    return re.findall(r"\d+", joined)


def survives(pattern: str, raw_span: str, text: str) -> bool:
    """`raw_span` 의 개인정보가 `text` 에 (오류가 섞였더라도) 읽을 수 있게 남아 있는가."""
    if not raw_span:
        raise ValueError("raw_span 이 비어 있으면 살아남음을 판정할 수 없다")
    if pattern in _NUMERIC:
        digits = re.sub(r"\D", "", raw_span)
        if not digits:
            raise ValueError(f"{pattern} 인데 raw_span 에 숫자가 없다: {raw_span!r}")
        need = min(len(digits), 4)
        return any(_longest_common_substring(digits, run) >= need for run in _digit_runs(text))
    need = _MIN_OVERLAP.get(pattern)
    if need is None:
        raise ValueError(f"모르는 패턴: {pattern}")
    compact = re.sub(r"\s+", "", raw_span)
    return _longest_common_substring(compact, re.sub(r"\s+", "", text)) >= min(need, len(compact))


@dataclass(frozen=True)
class RobustCase:
    item_id: str
    pattern: str
    outcome: str  # "masked" | "missed" | "erased"


def classify(item_id: str, pattern: str, raw_span: str, injected: str, masked: str) -> RobustCase:
    if not survives(pattern, raw_span, injected):
        return RobustCase(item_id, pattern, "erased")
    return RobustCase(item_id, pattern, "missed" if survives(pattern, raw_span, masked) else "masked")


def score(cases: list[RobustCase]) -> dict:
    """누락은 **건수**다 — 절대 규칙은 건 단위다(재현율 하나로 뭉개지 않는다)."""
    by_pattern: dict[str, dict[str, int]] = {}
    for c in cases:
        row = by_pattern.setdefault(c.pattern, {"masked": 0, "missed": 0, "erased": 0})
        row[c.outcome] += 1
    missed = [c for c in cases if c.outcome == "missed"]
    return {
        "miss_count": len(missed),
        "missed_items": [f"{c.item_id}({c.pattern})" for c in missed],
        "erased_count": sum(1 for c in cases if c.outcome == "erased"),
        "judged": sum(1 for c in cases if c.outcome != "erased"),
        "n": len(cases),
        "by_pattern": dict(sorted(by_pattern.items())),
    }
