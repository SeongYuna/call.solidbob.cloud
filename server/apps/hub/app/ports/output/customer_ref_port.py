# Requirement: SEC-1, SEC-2
from __future__ import annotations

from abc import ABC, abstractmethod


class InvalidPhoneNumber(ValueError):
    """숫자만 남겼을 때 전화번호 길이가 아니다. 메시지에 번호를 싣지 않는다."""


class CustomerRefPort(ABC):
    """발신 번호 → 고객 식별자(`customer.customer_id` · `blacklist_request.customer_ref`).

    **평문 번호는 이 포트 밖으로 나가지 않는다**(`decisions/205` ③·`decisions/304`). 같은 번호면 같은 값이
    나와야 재상담 이력·블랙리스트 조회가 이어진다. 규칙 계산이라 def 다.
    """

    @abstractmethod
    def ref(self, phone: str) -> str | None:
        """식별자. 비밀키가 없어 만들 수 없으면 None. 번호 형식이 아니면 `InvalidPhoneNumber`."""

    def hint(self, phone: str) -> str | None:
        """화면 표시용 뒤 4자리(`****1234`, `decisions/144` — 316 일부 철회). 기본은 없음 — 구현체가 켠다.
        뒤 4자리만이라 번호를 되돌릴 수 없고, HMAC 과 함께 저장돼도 전수 대입의 단서로는 부족하다(경우의 수 10^4 → 10^7)."""
        return None
