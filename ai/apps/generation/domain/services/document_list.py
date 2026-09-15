# Requirement: B-4, B-5, B-6
"""B-4 서류 목록 — 모델 출력을 **규칙으로 검사해** 카드 문구로 만든다.

rev.5 기획서가 B-4 를 「근거 기반 **서류 목록** 생성」으로 좁혔다(`_project/plan.md` §2.2 B). 그래서 모델에게 맡기는 일은
**조항 본문에서 서류 이름을 골라 적는 것**뿐이고, 나머지는 여기 규칙이 한다(절대 원칙 9 — 판정은 규칙이, 설명만 LLM이):

1. **근거 대조** — 모델이 적은 서류 이름이 **근거 조항 본문에 실제로 있어야** 카드에 싣는다. 없으면 버리고 센다(환각 1건)
2. **금지 표현** — 부록 A-1 의 판정·점수 표현이 섞인 항목은 버린다
3. **문구는 코드가 짓는다** — `"필요 서류: A · B"`. 모델 문장을 그대로 화면에 올리지 않으므로 판정 문장이 끼어들 틈이 없다
4. **남는 항목이 없으면 카드를 만들지 않는다** — 호출부가 스니펫 카드로 내려간다(지어내지 않는다)

순수 파이썬이다(`ai/.importlinter` 계약 3).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

# 모델이 「없음」이라고 답하는 모양들. 서류가 없는 조항(안내형)에서 나온다.
_NONE_MARKERS = ("없음", "없습니다", "해당 없음", "해당없음", "필요 서류 없음")

# 부록 A-1 · rfp-harness §1.5 — 판정·점수·보장 표현. 서류 이름에 섞여 나오면 그 항목을 버린다.
FORBIDDEN_TERMS = ("안전합니다", "위험도", "등급", "점수", "%", "확실", "무조건", "보장", "틀림없")

_BULLET = re.compile(r"^\s*(?:[-*•·▪]|\d+[.)])\s*")
_MARKUP = re.compile(r"[*_`#>\[\]]")
_TRAIL = re.compile(r"[\s.,;:!?。]+$")


def normalize(text: str) -> str:
    """대조용 — 공백·마크다운·문장부호를 뺀다. 서류 이름의 띄어쓰기 차이(`신분증 사본`/`신분증사본`)를 흡수한다."""
    return re.sub(r"[\s*_`#>\[\]().,;:!?·•\-\"'「」『』]", "", text)


_PAREN = re.compile(r"\s*[(（][^)）]*[)）]")
_SPECIAL = re.compile(r"<\|[^|]*\|>")  # 채팅 템플릿 특수 토큰이 새어 나온 것(<|eot_id|> 등)


def _json_documents(output: str) -> list[str] | None:
    try:
        data = json.loads(_SPECIAL.sub("", output).strip())
    except ValueError:
        return None
    docs = data.get("documents") if isinstance(data, dict) else data  # 배열만 낸 경우도 받는다(스키마 없는 대조군)
    return [d for d in docs if isinstance(d, str)] if isinstance(docs, list) else None


def parse_items(output: str) -> list[str]:
    """모델 출력 → 서류 이름 목록. JSON(`{"documents": [...]}`)이면 배열을, 아니면 줄 단위로 읽는다.

    **괄호 설명은 뗀다** — `"위임장 (대리인 서명 필수)"` 의 괄호는 모델이 붙인 말이라 조항에 없고, 화면 문구는 코드가
    짓기 때문에 이름만 남기면 된다. 줄머리 기호·번호를 떼고, 쉼표로 여럿 적으면 가른다. 중복은 한 번만.
    """
    documents = _json_documents(output)
    lines = documents if documents is not None else output.splitlines()
    items: list[str] = []
    for line in lines:
        line = _SPECIAL.sub("", _PAREN.sub("", line)).strip().strip('"\'[]')
        line = _MARKUP.sub("", _BULLET.sub("", line)).strip()
        if not line or line.endswith(":"):
            continue
        for piece in re.split(r"[,，、]|\s+및\s+|\s+와\s+|\s+과\s+", line):
            piece = _TRAIL.sub("", piece.strip().strip('"\''))
            if piece and piece not in items:
                items.append(piece)
    return items


def is_none_answer(output: str) -> bool:
    documents = _json_documents(output)
    if documents is not None:
        return not any(normalize(d) for d in documents)
    compact = normalize(output)
    return not compact or any(compact == normalize(m) for m in _NONE_MARKERS)


@dataclass(frozen=True)
class ItemCheck:
    grounded: tuple[str, ...]
    ungrounded: tuple[str, ...] = field(default_factory=tuple)  # 근거 조항에 없는 이름 — **환각**
    forbidden: tuple[str, ...] = field(default_factory=tuple)

    @property
    def hallucinated(self) -> int:
        return len(self.ungrounded)


def check_items(items: list[str], source_text: str) -> ItemCheck:
    """항목마다 근거 조항에 있는지·금지 표현이 없는지 본다."""
    src = normalize(source_text)
    grounded, ungrounded, forbidden = [], [], []
    for it in items:
        if any(t in it for t in FORBIDDEN_TERMS):
            forbidden.append(it)
        elif normalize(it) and normalize(it) in src:
            grounded.append(it)
        else:
            ungrounded.append(it)
    return ItemCheck(tuple(grounded), tuple(ungrounded), tuple(forbidden))


MAX_ITEMS = 8  # 카드 한 장에 서류가 이보다 많으면 조항을 그대로 보는 게 낫다 — 넘치면 자른다(순서 유지)


def compose_summary(items: tuple[str, ...]) -> str:
    return "필요 서류: " + " · ".join(items[:MAX_ITEMS])


SYSTEM_PROMPT = (
    "조항 본문에 적힌 구비서류 이름만 본문 표현 그대로 documents 배열에 넣는다. "
    "설명·조건·괄호 설명을 넣지 않는다. 본문에 없는 서류는 넣지 않는다. 본문에 서류가 없으면 빈 배열로 둔다."
)

# 출력 모양을 **디코딩 단계에서** 강제한다(Ollama `format` = JSON 스키마). 2026-09-15 두 번의 실패 뒤에 골랐다 —
#   ① 지시문만: EXAONE 1.2B 가 마크다운 설명문을 써서 96장 중 81장에 조항에 없는 말이 섞였다
#   ② 지시문 + 가상 예시 두 쌍: 형식은 나아졌지만 **예시 속 말(「도서관」·「공원 개방 시간」)이 답에 새어 들어왔다** —
#      환각을 줄이려던 장치가 환각의 출처가 됐다. 예시는 걷었다
# 스키마는 모양만 강제한다 — 배열 안에 조항에 없는 말이 들어오는 것은 그대로라 근거 대조가 여전히 필요하다.
DOCUMENTS_SCHEMA: dict = {
    "type": "object",
    "properties": {"documents": {"type": "array", "items": {"type": "string"}}},
    "required": ["documents"],
}


def build_messages(utterance: str, title: str, text: str) -> list[dict[str, str]]:
    """프롬프트. 고객 발화는 **마스킹본**이어야 한다(SEC-1 — 호출부 책임, `GenerationPort` 계약)."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"고객 문의: {utterance}\n조항 제목: {title}\n조항 본문:\n{text}"},
    ]
