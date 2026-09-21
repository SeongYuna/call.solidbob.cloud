# Requirement: C-5, SEC-1
"""MaskingPort 프로바이더. 2026-08-27 부터 규칙 기반 구현이 기본이다(지금은 P1~P7 — 아래).

그 전까지는 501 이었다 — 마스킹 없이 원문을 흘려보내는 '임시 통과' 구현을 만들지 않기
위해서였다(SEC-1: 그 경로가 생기는 순간 원문이 새는 길이 된다). 이제 실제 구현이 있으므로
501 이 아니다.

**P6·P7(인명·상세주소)도 규칙으로 처리한다**(`masking/domain/services/name_detector.py`·`address_detector.py`,
2026-09-17·18 보강). 다만 **부분 지원**이다 — 이름은 밝히는 문맥이 있을 때만, 주소는 어절이 둘 이상 이어질 때만 잡는다
(`rule_masking_adapter.py` `PARTIAL_PATTERNS`). NER 은 `PII_NER_MODEL_DIR` 이 있을 때 `server/main.py` 가 이 위에 합집합으로 얹는다.
(옛 서술 「P6·P7 은 아직 없다 · P1~P5 만」은 2026-09-21 에 걷었다.)
"""

from __future__ import annotations

from hub.app.ports.output.masking_port import MaskingPort
from masking.adapter.outbound.rule_masking_adapter import RuleMaskingAdapter


def get_masking_port() -> MaskingPort:
    return RuleMaskingAdapter()
