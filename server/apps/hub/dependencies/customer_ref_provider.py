# Requirement: SEC-1, SEC-2
from __future__ import annotations

from fastapi import Request

from hub.adapter.outbound.hmac_customer_ref_adapter import HmacCustomerRefAdapter
from hub.app.ports.output.customer_ref_port import CustomerRefPort


def get_customer_ref_port(request: Request) -> CustomerRefPort:
    return HmacCustomerRefAdapter(request.app.state.settings.customer_ref_hmac_key)
