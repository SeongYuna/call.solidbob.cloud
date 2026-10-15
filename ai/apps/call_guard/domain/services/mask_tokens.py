# Requirement: C-6, C-5
"""분류기에 넣기 전 가림 표시(우리 마스킹 「*」 · AI Hub 비식별 「O」)를 지운다 — 순수 파이썬.

학습한 분류기는 가림 표시 덩어리(「***-****-****」)에 반응해 폭언으로 붙였다(2026-10-15 실측: AI Hub 실제 고객 발화 1만 건 중
오탐 43 → 지우면 10, 외부 평가 재현율은 그대로 — `decisions/223` 결과). 규칙 사전에는 쓰지 않는다(사전은 낱말을 본다).
"""
from __future__ import annotations

import re

_MASK = re.compile(r"[O○*＊]{2,}|[O○*＊](?=[-\s,.)]|$)")


def strip_mask_tokens(text: str) -> str:
    out = _MASK.sub(" ", text)
    out = re.sub(r"(?<!\w)[-,]+(?!\w)", " ", out)   # 가림 표시 사이에 남은 구분자만(낱말에 붙은 것은 둔다)
    return re.sub(r"\s+", " ", out).strip()
