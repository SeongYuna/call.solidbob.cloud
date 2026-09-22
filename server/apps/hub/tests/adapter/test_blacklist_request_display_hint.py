# Requirement: J-2, C-5, SEC-1, QUA-1
"""`display_hint` 는 채우지 않는다(`decisions/316`) — 전화번호 뒷자리도 P4 의 일부다.

응답 스키마가 DTO 에서 어떤 값을 받아도 `display_hint` 를 싣지 않고, 요청 항목 어디에도 P4 조각이 나가지 않음을 고정한다.
"""

import re

from hub.adapter.inbound.api.schemas.blacklist_request_create_schema import BlacklistRequestItemSchema
from hub.app.dtos.blacklist_dto import BlacklistRequest, RequestEvidence


def _item(**kw):
    return BlacklistRequestItemSchema.from_dto(BlacklistRequest(
        request_id="7", call_id="c_001", customer_ref="f" * 64, requested_by="agent-7", reason="반복 폭언",
        context_excerpt="제 번호는 *********** 입니다", evidence=RequestEvidence(), **kw))


def test_display_hint_는_늘_null이다():
    assert _item().display_hint is None


def test_요청_항목_JSON_어디에도_전화번호_조각이_없다():
    body = _item().model_dump_json()
    assert not re.search(r"\d{4}", body.replace("f" * 64, ""))  # 뒤 4자리 같은 숫자 조각이 없다


def test_온도_이상은_미측정이면_null_로_나간다():
    """0(이상 없음)과 구분된다(`decisions/316`)."""
    assert _item().evidence.temperature_outliers is None
    measured = BlacklistRequestItemSchema.from_dto(BlacklistRequest(
        request_id="7", call_id="c", customer_ref="r", requested_by="a", reason="x", context_excerpt="y",
        evidence=RequestEvidence(temperature_outliers=0)))
    assert measured.evidence.temperature_outliers == "0"
