# Requirement: D-2, E-1
"""D-2 정답 파일의 유형표가 **운영 D-2 제안기**(`server/apps/postcall`, `decisions/323`)의 유형표와 같은지 — 합성 루트 테스트다.

하네스는 운영과 같은 `RulePostcallAdapter`(server)를 채점한다. 정답 파일이 유형표를 **복사해** 들고 있으니, 복사본이 원본과 갈라지면
유형 정확도가 조용히 0 이 된다 — 2026-09-22 실제로 그랬다(정답은 `ai/` 의 옛 유형표 「대중교통 안내」, 운영은 「대중교통」). 여기서 막는다.
"""

from __future__ import annotations

import json

from evaluation.golden_set import DEFAULT_POSTCALL_SET_PATH
from postcall.domain.services.inquiry_rules import INQUIRY_RULES


def test_정답_파일_유형표는_운영_D2_제안기_유형표와_같다():
    raw = json.loads(DEFAULT_POSTCALL_SET_PATH.read_text(encoding="utf-8"))
    assert tuple(raw["type_catalogue"]["types"]) == tuple(name for name, _ in INQUIRY_RULES)


def test_정답_라벨은_전부_유형표_안에_있다():
    raw = json.loads(DEFAULT_POSTCALL_SET_PATH.read_text(encoding="utf-8"))
    types = set(raw["type_catalogue"]["types"])
    calls = raw.get("calls") or raw.get("items")
    assert all(c["inquiry_type"] in types for c in calls)
