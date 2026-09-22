# Requirement: J-1, J-2, J-4, QUA-1
"""블랙리스트 인터랙터 테스트가 함께 쓰는 스텁 포트 — 저장 없이 호출만 기록한다."""

from dataclasses import replace
from datetime import datetime, timezone

from hub.app.dtos.blacklist_dto import BlacklistEntry, BlacklistRequest, ExpiryChange, RequestEvidence
from hub.app.dtos.blacklist_request_create_dto import CallEvidence
from hub.app.ports.output.blacklist_evidence_port import BlacklistEvidencePort
from hub.app.ports.output.blacklist_port import BlacklistPort
from hub.app.ports.output.masking_port import MaskingPort

NOW = datetime(2026, 9, 14, 3, 0, tzinfo=timezone.utc)
REF = "f" * 64


class StubBlacklist(BlacklistPort):
    def __init__(self):
        self.calls = []

    async def save_request(self, request):
        self.calls.append(("save", request))
        return replace(request, request_id="7", requested_at=NOW, evidence_snapshot_at=NOW)

    async def list_requests(self, status=None, requested_by=None):
        self.calls.append(("list_requests", status) if requested_by is None else ("list_requests", status, requested_by))
        return []

    async def decide(self, request_id, *, approve, decided_by, expires_at, note):
        self.calls.append(("decide", request_id, approve, decided_by, expires_at, note))
        return BlacklistRequest(request_id=request_id, call_id="c1", customer_ref=REF, requested_by="a1",
                                reason="r", context_excerpt="x", status="approved" if approve else "rejected")

    async def find_entry(self, customer_ref):
        return None

    async def list_entries(self, active_only=False):
        self.calls.append(("list_entries", active_only))
        return []

    async def release_entry(self, entry_id, *, released_by, reason):
        self.calls.append(("release", entry_id, released_by, reason))
        return BlacklistEntry(entry_id=entry_id, customer_ref=REF, request_id="7", released_by=released_by,
                              release_reason=reason)

    async def change_expiry(self, entry_id, *, changed_by, expires_at, reason):
        self.calls.append(("change_expiry", entry_id, changed_by, expires_at, reason))
        entry = BlacklistEntry(entry_id=entry_id, customer_ref=REF, request_id="7", approved_at=NOW, expires_at=expires_at)
        return entry, ExpiryChange(change_id=1, entry_id=entry_id, previous_expires_at=NOW, new_expires_at=expires_at,
                                   changed_by=changed_by, reason=reason, changed_at=NOW)

    async def list_expiry_changes(self, entry_id):
        self.calls.append(("list_expiry_changes", entry_id))
        return []

    async def purge_retained_texts(self):
        from hub.app.dtos.blacklist_retention_dto import RetentionPurgeResult

        self.calls.append(("purge",))
        return RetentionPurgeResult(retention_days=180, cutoff=NOW, expiry_change_reasons_purged=2, rejected_requests_purged=1)


class StubEvidence(BlacklistEvidencePort):
    def __init__(self, collected: CallEvidence | None):
        self.collected = collected

    async def collect(self, call_id):
        return self.collected


class DigitMasking(MaskingPort):
    """숫자를 `*` 로 — 사유·메모가 저장 전에 마스킹을 거치는지 보려는 흉내."""

    def mask(self, text):
        return "".join("*" if ch.isdigit() else ch for ch in text), ()


def evidence(customer_ref=REF, distress=0) -> CallEvidence:
    return CallEvidence(
        customer_ref=customer_ref,
        evidence=RequestEvidence(call_duration_s=600, insult_count=3, distress_count=distress),
        context_excerpt="이런 *** 같은",
    )
