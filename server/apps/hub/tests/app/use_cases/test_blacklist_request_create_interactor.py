# Requirement: J-1, J-2, SEC-1, QUA-1
import asyncio

import pytest

from hub.app.dtos.blacklist_request_create_dto import BlacklistRequestCreateCommand
from hub.app.ports.output.blacklist_port import BlacklistConflict, BlacklistNotFound
from hub.app.use_cases.blacklist_request_create_interactor import BlacklistRequestCreateInteractor

from ._blacklist_stubs import REF, DigitMasking, StubBlacklist, StubEvidence, evidence


def _run(collected, **kw):
    blacklist = StubBlacklist()
    cmd = BlacklistRequestCreateCommand(**{"call_id": "c1", "requested_by": "agent-7", "reason": "반복 폭언 010-1234-5678", **kw})
    result = asyncio.run(BlacklistRequestCreateInteractor(blacklist, StubEvidence(collected), DigitMasking()).create(cmd))
    return result, blacklist


def test_서버가_모은_근거로_pending_요청을_남기고_사유는_마스킹한다():
    result, blacklist = _run(evidence())
    saved = blacklist.calls[0][1]
    assert saved.status == "pending" and saved.customer_ref == REF
    assert saved.reason == "반복 폭언 ***-****-****"
    assert saved.context_excerpt == "이런 *** 같은" and saved.evidence.insult_count == 3
    assert result.request.request_id == "7" and result.has_distress is False


def test_위기_신호는_막지_않고_경고_표시만_돌려준다():
    """MANUAL-5.4 — 도움이 필요한 사람을 차단으로 올리지 않도록 화면이 안내를 띄운다. 판단은 사람이."""
    result, _ = _run(evidence(distress=1))
    assert result.has_distress is True


def test_통화가_없으면_NotFound_고객이_식별_안_됐으면_Conflict():
    with pytest.raises(BlacklistNotFound):
        _run(None)
    with pytest.raises(BlacklistConflict):
        _run(evidence(customer_ref=None))


@pytest.mark.parametrize("kw", [{"reason": "  "}, {"requested_by": " "}])
def test_빈_사유_빈_요청자는_거부한다(kw):
    with pytest.raises(ValueError):
        _run(evidence(), **kw)
