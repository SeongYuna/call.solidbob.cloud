# Requirement: SEC-1, SEC-2, QUA-1
"""발신 번호 → 고객 식별자. 같은 번호는 같은 값, 평문은 어디에도 남지 않는다."""

import pytest

from hub.adapter.outbound.hmac_customer_ref_adapter import HmacCustomerRefAdapter, normalize_phone
from hub.app.ports.output.customer_ref_port import InvalidPhoneNumber


@pytest.mark.parametrize("raw", ["010-1234-5678", "01012345678", "+82 10 1234 5678", "(010) 1234 5678"])
def test_표기가_달라도_같은_번호로_맞춘다(raw):
    assert normalize_phone(raw) == "01012345678"


def test_같은_번호는_같은_식별자_다른_키는_다른_식별자():
    a = HmacCustomerRefAdapter("key-a")
    assert a.ref("010-1234-5678") == a.ref("+82 10 1234 5678")
    assert len(a.ref("01012345678")) == 64
    assert a.ref("01012345678") != HmacCustomerRefAdapter("key-b").ref("01012345678")


def test_식별자에_번호가_들어있지_않다():
    assert "01012345678" not in HmacCustomerRefAdapter("key").ref("01012345678")


def test_키가_없으면_만들지_않는다():
    """평문이나 키 없는 해시로 대신하지 않는다 — 전화번호는 전수 대입으로 되돌려진다."""
    assert HmacCustomerRefAdapter(None).ref("01012345678") is None


@pytest.mark.parametrize("raw", ["", "1234", "010-1234-5678-9999", "전화번호"])
def test_번호_형식이_아니면_거부하고_메시지에_입력을_싣지_않는다(raw):
    with pytest.raises(InvalidPhoneNumber) as exc:
        HmacCustomerRefAdapter("key").ref(raw)
    assert raw == "" or raw not in str(exc.value)
