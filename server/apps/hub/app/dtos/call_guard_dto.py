# Requirement: C-6
from __future__ import annotations

from dataclasses import dataclass

# 응대매뉴얼 5장이 나눈 갈래를 그대로 쓴다(`knowledge-base/dasan/manual/MANUAL.md`).
# **`distress` 를 나머지 셋과 같은 자리에 두지 않는 것이 이 계약의 요점이다** — 5.4 조가
# 위기 신호는 통화를 종료하지 않고 전문 기관으로 연결하라고 정한다. 하나로 뭉치면
# 화면이 그 차이를 표현할 수 없고, 잘못 뭉친 채로 "폭언 탐지 재현율 0.9"라고 적게 된다.
ABUSE_CATEGORIES = ("insult", "threat", "sexual")
DISTRESS_CATEGORY = "distress"


@dataclass(frozen=True)
class CallGuardFlag:
    """C-6 — **고객** 발화에서 잡힌 폭언·위기 신호 1건.

    C-1~C-4(`ComplianceFinding`)와 모양이 비슷하지만 **화자가 다르다.** 저쪽은 상담원의
    발화를 규제하고 이쪽은 고객의 발화로부터 상담원을 보호한다. 대체가 아니라 추가다
    (`_project/decisions/201`).

    ⚠ **위험도 점수를 담지 않는다.** [부록 A-1](/docs/12/)이 "위험도 78%입니다" 류 수치
    표기를 금지하고, 판정은 규칙이 한다(절대 원칙 9). `category` 는 대응 갈래이지
    점수가 아니다.
    """

    category: str  # "insult" | "threat" | "sexual" | "distress"
    phrase: str  # 걸린 표현 — **마스킹된 자막에서 잘라낸다**(MANUAL-5.5)
    source_doc_id: str | None = None  # 근거 조항 (DASAN-MANUAL-5.x)

    def __post_init__(self) -> None:
        allowed = ABUSE_CATEGORIES + (DISTRESS_CATEGORY,)
        if self.category not in allowed:
            raise ValueError(
                f"'{self.category}' 는 콜 가드 갈래가 아닙니다 (가능: {', '.join(allowed)})"
            )

    @property
    def is_distress(self) -> bool:
        """위기 신호인가. 화면·에스컬레이션이 폭언과 **다르게** 다뤄야 하는 갈래다(5.4 조)."""
        return self.category == DISTRESS_CATEGORY
