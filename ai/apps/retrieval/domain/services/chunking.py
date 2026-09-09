# Requirement: B-2
"""지식베이스 마크다운 → 색인 청크. 순수 규칙 계산이므로 domain 계층에 둔다.

**1 조항 = 1 청크.** 각 조항은 `knowledge-base/` 안에 `<!-- id: DASAN-TERM-1.1 -->` 주석으로
이미 경계와 ID 가 표시돼 있고, 그 ID 가 골든셋 `expected_doc_ids` 의 단위다. 고정 길이로
자르면 조항 경계를 넘나들어 청크 하나가 여러 조항에 걸치고, 그러면 Recall@5 를 채점할 수
없다 — 그래서 상한(`MAX_CHARS`)을 넘는 조항만 예외적으로 쪼갠다.

2026-08-26 실측: 조항 102개, 중앙값 101자 / 최대 332자 / 400자 초과 0건 → 현재 지식베이스에서
분할은 일어나지 않는다. 상한은 문서가 길어질 때를 대비한 안전장치다.
"""

from __future__ import annotations

import re

from ..value_objects.chunk import DOMAIN_BY_PREFIX, Chunk

MAX_CHARS = 400

_ID_MARKER = re.compile(r"<!--\s*id:\s*([A-Z]+(?:-[A-Z0-9.]+)+)\s*-->")
_HEADING = re.compile(r"^#{2,6}\s+(.*)$", re.MULTILINE)


def parse_doc_id(doc_id: str) -> tuple[str, str]:
    """`DASAN-TERM-3.2` → ("dasan", "TERM"). 접두어를 모르면 ValueError."""
    parts = doc_id.split("-")
    if len(parts) < 3:
        raise ValueError(f"조항 ID 형식이 아니다: {doc_id!r}")
    domain = DOMAIN_BY_PREFIX.get(parts[0])
    if domain is None:
        raise ValueError(f"모르는 도메인 접두어: {doc_id!r}")
    return domain, parts[1]


def _split(text: str, limit: int) -> list[str]:
    """상한을 넘는 조항만 문단 경계에서 자른다. 한 문단이 통째로 상한을 넘으면 그대로 둔다
    (문장 중간을 끊으면 조항 하나가 검색에도 화면에도 반토막으로 보인다)."""
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    current = ""
    for para in text.split("\n\n"):
        candidate = f"{current}\n\n{para}" if current else para
        if current and len(candidate) > limit:
            parts.append(current)
            current = para
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts


def chunk_markdown(source: str, *, max_chars: int = MAX_CHARS) -> list[Chunk]:
    """마크다운 한 편을 조항 단위 청크로 자른다. ID 마커가 없는 머리말은 버린다."""
    chunks: list[Chunk] = []
    matches = list(_ID_MARKER.finditer(source))
    for i, m in enumerate(matches):
        doc_id = m.group(1)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(source)
        body = source[m.end() : end]

        heading = _HEADING.search(body)
        title = heading.group(1).strip() if heading else doc_id
        text = _HEADING.sub("", body, count=1) if heading else body
        # 조항 사이 구분선(---)은 조항 본문이 아니다
        text = re.sub(r"^\s*---\s*$", "", text, flags=re.MULTILINE).strip()

        domain, doc_type = parse_doc_id(doc_id)
        pieces = _split(text, max_chars)
        for part, piece in enumerate(pieces):
            chunks.append(
                Chunk(
                    chunk_id=doc_id if len(pieces) == 1 else f"{doc_id}#{part}",
                    doc_id=doc_id,
                    domain=domain,
                    doc_type=doc_type,
                    title=title,
                    text=piece.strip(),
                    part=part,
                )
            )
    return chunks
