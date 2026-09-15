# Requirement: B-4, B-5, E-2
"""B-4 생성 채점 — **규칙으로만** 센다(절대 원칙 1). `w6-hallucination-eval`.

⚠ **생성기의 검사 규칙(`generation/domain/services/document_list.py`)을 import 하지 않는다.** 그걸 가져다 쓰면
생성기가 자기 필터로 자기를 채점하는 것이 된다 — 필터에 구멍이 있으면 채점에도 같은 구멍이 난다.
`ai/.importlinter` 계약 2(모듈 상호 독립)도 이것을 막는다. 그래서 대조 규칙을 **여기서 따로** 세우고, 일부러 더 엄격하게 둔다:

| 무엇 | 규칙 |
|---|---|
| 출처 표시 | 카드마다 `source.doc_id` 가 비어 있지 않다 |
| 원출력 환각 | 모델 원출력의 줄·쉼표 단위 조각 중 **근거 조항 본문에 없는 것**(제목은 넣지 않는다 — 조항 제목을 서류 이름처럼 옮긴 것도 센다). 「없음」·빈 배열은 0건 |
| 카드 환각 | 화면에 나간 `summary` 가 `필요 서류:` 로 시작하면 그 목록 항목이 근거에 없는 것. 스니펫 카드는 원문 그대로라 0건 |
| 금지 표현 | 카드 문구에 부록 A-1 판정·점수 표현 |

«근거에 있다» = 공백·문장부호·마크다운을 뺀 문자열이 근거 조항 안에 **그대로** 들어 있다. 의미가 같은 다른 말(`신분증`↔`주민등록증`)은
**환각으로 센다** — 조항에 없는 이름을 화면에 쓴 것이기 때문이다. 이 기준으로 못 잡는 몫(맞는 이름인데 고객 절차에 안 맞는 서류)은
**규칙으로 재지 않았고 사람이 세지도 않았다** — 셀 때는 센 사람·기준·날짜를 함께 적는다.
"""

from __future__ import annotations

import json
import re

_STRIP = re.compile(r"[\s*_`#>\[\]().,;:!?·•\-\"'「」『』]")
_FORBIDDEN = ("안전합니다", "위험도", "등급", "점수", "%", "확실", "무조건", "보장", "틀림없")
_NONE = {"없음", "없습니다", "해당없음"}
SUMMARY_PREFIX = "필요 서류:"


def _norm(s: str) -> str:
    return _STRIP.sub("", s)


def _fragments(raw: str) -> list[str]:
    """원출력 → 채점 조각. JSON(`documents` 배열)이면 원소를, 아니면 줄을 본다. **괄호를 떼지 않는다** —
    생성기는 괄호 설명을 떼고 화면에 싣지만, 채점은 모델이 조항에 없는 말을 **썼는가** 를 센다(원출력 환각)."""
    try:
        data = json.loads(re.sub(r"<\|[^|]*\|>", "", raw).strip())
        arr = data.get("documents", []) if isinstance(data, dict) else data
        lines = [d for d in arr if isinstance(d, str)] if isinstance(arr, list) else None
    except ValueError:
        lines = None
    out = []
    for line in (lines if lines is not None else raw.splitlines()):
        line = re.sub(r"^\s*(?:[-*•·▪]|\d+[.)])\s*", "", line).strip()
        if not line or line.rstrip().endswith(":"):
            continue
        for piece in re.split(r"[,，、]", line):
            if _norm(piece):
                out.append(piece.strip())
    return out


def raw_hallucinations(raw_output: str, source: str) -> list[str]:
    """모델 원출력에서 근거 조항에 없는 조각. 「없음」 답이면 빈 목록."""
    if _norm(raw_output) in _NONE or not _fragments(raw_output):
        return []
    src = _norm(source)
    return [f for f in _fragments(raw_output) if _norm(f) not in src]


def card_hallucinations(summary: str, source: str) -> list[str]:
    """화면에 나간 문구의 환각. 서류 목록 카드만 본다 — 스니펫 카드는 조항 원문이다."""
    if not summary.startswith(SUMMARY_PREFIX):
        return []
    src = _norm(source)
    items = [i.strip() for i in summary[len(SUMMARY_PREFIX):].split("·")]
    return [i for i in items if _norm(i) and _norm(i) not in src]


def forbidden_hits(summary: str) -> list[str]:
    return [t for t in _FORBIDDEN if t in summary]


def score_generation(rows: list[dict]) -> dict:
    """행 1건 = 생성한 카드 1장. 키: `doc_id` · `summary` · `source_text` · `raw_output` · `outcome`."""
    cards = len(rows)
    with_source = sum(1 for r in rows if r.get("doc_id"))
    raw = [(r, raw_hallucinations(r.get("raw_output", ""), r["source_text"])) for r in rows if r.get("outcome") != "error"]
    shipped = [(r, card_hallucinations(r["summary"], r["source_text"])) for r in rows]
    return {
        "cards": cards,
        "source_rate": with_source / cards if cards else float("nan"),
        "raw_hallucinated_cards": sum(1 for _, h in raw if h),
        "raw_hallucinated_items": sum(len(h) for _, h in raw),
        "shipped_hallucinated_cards": sum(1 for _, h in shipped if h),
        "forbidden_cards": sum(1 for r in rows if forbidden_hits(r["summary"])),
        "outcomes": {k: sum(1 for r in rows if r.get("outcome") == k) for k in ("generated", "none", "no_grounded_items", "error")},
    }
