# Requirement: SEC-1, SEC-2
"""CustomerRefPort 구현 — `HMAC-SHA256(숫자만 남긴 번호, CUSTOMER_REF_HMAC_KEY)` 의 hex 64자.

- **정규화가 곧 식별이다.** `010-1234-5678`·`01012345678`·`+82 10 1234 5678` 이 같은 고객이어야 한다.
  국가번호 `82` 로 시작하면 앞자리 `0` 으로 되돌린다 — 국내 번호 표기를 한 가지로 맞춘다
- 해시가 아니라 HMAC 인 이유: 전화번호는 경우의 수가 작아 **키 없는 해시는 전수 대입으로 되돌려진다**(`decisions/205` ③)
- 키가 없으면 None — 평문이나 키 없는 해시로 대신하지 않는다
"""

from __future__ import annotations

import hashlib
import hmac

from hub.app.ports.output.customer_ref_port import CustomerRefPort, InvalidPhoneNumber

# 국내 유선·휴대 번호 자릿수(지역번호 포함 9~11) — 국제 표기(+82)를 되돌린 뒤 본다.
_MIN_DIGITS = 9
_MAX_DIGITS = 11


def normalize_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    if digits.startswith("82") and len(digits) >= _MIN_DIGITS + 1:
        digits = "0" + digits[2:]
    if not _MIN_DIGITS <= len(digits) <= _MAX_DIGITS:
        raise InvalidPhoneNumber("발신 번호 형식이 아닙니다 (숫자 9~11자리)")
    return digits


class HmacCustomerRefAdapter(CustomerRefPort):
    def __init__(self, key: str | None) -> None:
        self._key = key.encode("utf-8") if key else None

    def ref(self, phone: str) -> str | None:
        digits = normalize_phone(phone)  # 키가 없어도 형식은 본다 — 잘못된 입력을 조용히 넘기지 않는다
        if self._key is None:
            return None
        return hmac.new(self._key, digits.encode("ascii"), hashlib.sha256).hexdigest()
