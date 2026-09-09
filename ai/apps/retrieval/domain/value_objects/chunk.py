# Requirement: B-2
from __future__ import annotations

from dataclasses import dataclass

# 2026-08-28 다산콜센터 단일 도메인으로 줄였다(`_project/decisions/201`).
# 금융보험·쇼핑·질병관리본부는 지식베이스·골든셋과 함께 삭제됐다.
#
# 튜플·딕셔너리 형태를 유지하는 이유: 도메인이 하나여도 순회·검증 코드가 그대로 돌고,
# 나중에 되돌리거나 늘릴 때 이 두 줄만 고치면 된다. 값 하나짜리 상수로 납작하게 만들면
# 그 코드를 전부 다시 써야 한다.
DOMAINS = ("dasan",)
DOC_TYPES = ("TERM", "MANUAL", "POLICY")

# 도메인 접두어(knowledge-base 폴더명 ↔ 문서 ID 접두어). domain.md §3 의 표와 같다.
DOMAIN_BY_PREFIX = {"DASAN": "dasan"}


@dataclass(frozen=True)
class Chunk:
    """색인 단위 1건. 조항 하나가 그대로 청크 하나가 된다(2026-08-26 실측 근거는 티켓 참고).

    `doc_id` 는 골든셋 `expected_doc_ids` 와 대조되는 단위라 **조항 ID 그대로**여야 한다.
    조항이 상한을 넘어 쪼개진 경우에만 `chunk_id` 가 `doc_id` 와 달라진다(`DASAN-TERM-3.2#1`).
    """

    chunk_id: str
    doc_id: str
    domain: str  # "dasan" — 2026-08-28 이후 값이 하나뿐이다
    doc_type: str  # "TERM" | "MANUAL" | "POLICY"
    title: str
    text: str
    part: int = 0  # 조항 안에서 몇 번째 조각인지. 분할이 없으면 0
