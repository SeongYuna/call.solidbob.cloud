# Requirement: D-2, E-1
"""D-2 정답 파일의 유형표가 `postcall_summary` 가 실제로 내는 유형표와 같은지 — 두 모듈을 동시에 봐야 해서 합성 루트 테스트다.

`evaluation` 은 `postcall_summary` 를 import 할 수 없다(`ai/.importlinter` 계약 2). 그래서 정답 파일이 유형표를 **복사해** 들고 있고,
복사본이 원본과 갈라지면 유형 정확도가 조용히 0 이 된다 — 여기서 막는다.
"""

from __future__ import annotations

import json

from evaluation.golden_set import DEFAULT_POSTCALL_SET_PATH
from postcall_summary.domain.services.rules import INQUIRY_TYPES


def test_정답_파일_유형표는_D2_제안기_유형표와_같다():
    raw = json.loads(DEFAULT_POSTCALL_SET_PATH.read_text(encoding="utf-8"))
    assert tuple(raw["type_catalogue"]["types"]) == INQUIRY_TYPES
