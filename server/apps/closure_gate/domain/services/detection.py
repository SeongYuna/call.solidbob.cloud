# Requirement: F-2
"""판정 ② — 상담원이 서류를 **안내했는가**를 발화에서 본다. **규칙이다 — 생성 모델은 여기 없다** (절대 원칙 9).

서류마다 키워드(`RequiredDocument.keywords`)를 두고, 상담원의 확정 발화(마스킹본) 어디에든 있으면 안내한 것으로 센다.
공백은 무시한다(「신분 증」·「통장 사본」 전사 차이).

⚠ **한계 — 주장 범위를 넘지 않는다.**
- **부정 문맥을 모른다.** 「신분증은 필요 없어요」도 안내로 센다. 이 오류는 **누락을 못 잡는 쪽**이라 F-2 절대 규칙
  (누락 0건 탐지)에 불리하다. 채점은 골든셋 필요서류 케이스로 한다 — 2026-09-14 현재 0건이라 **측정 불가**다
- 짧은 키워드(「관계」·「소유」·「수리」)는 다른 맥락에서도 걸린다 — 역시 누락을 가리는 쪽이다
- 고객 발화는 보지 않는다 — 고객이 먼저 말한 서류를 상담원이 안내한 것으로 치면 안 된다
"""

from __future__ import annotations

from ..value_objects.closure_rule import ClosureRule


def _squash(text: str) -> str:
    return "".join(text.split())


def informed_documents(rule: ClosureRule, agent_utterances: list[str]) -> dict[str, bool]:
    """규칙의 필수 서류마다 안내했는지. 키 순서는 규칙표 순서다."""
    spoken = _squash(" ".join(agent_utterances))
    return {
        doc.name: any(_squash(keyword) in spoken for keyword in doc.keywords)
        for doc in rule.required
    }
