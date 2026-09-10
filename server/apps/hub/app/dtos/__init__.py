# Requirement: 7.3절 인터페이스 계약 v2
"""허브 DTO — 7.3절 계약 3종 + 포트가 나르는 값 객체. 필드명은 계약 JSON 과 글자 단위로 같다
(게이트웨이·대시보드가 같은 이름을 본다).

frozen dataclass 를 쓴다: 값 객체이고, pydantic 스키마는 HTTP 표면(adapter) 몫이다 (docs/architecture.md §3 규칙 3).
판정·규칙은 여기 두지 않는다 — DTO 는 나르기만 한다. F-2 판정은 closure_gate 스포크의 domain 이 한다.
"""

from .call_start_dto import CallDomain, CallStartCommand, CallStarted
from .call_summary_dto import CallSummaryDraft, FollowUpAction
from .closure_dto import ClosureCheckCommand
from .closure_verdict_dto import ClosureType, ClosureVerdict, Verdict
from .compliance_dto import ComplianceCheckCommand, ComplianceCheckResult
from .compliance_finding_dto import ComplianceFinding
from .domain_classification_dto import DomainClassification
from .myself_dto import MyselfQuery, MyselfResult
from .postcall_dto import PostcallCommand
from .recommendation_card_dto import Card, RecommendationCards, Source
from .recommendation_dto import RecommendCommand, RecommendResult
from .retrieved_doc_dto import RetrievedDoc
from .search_dto import SearchQuery, SearchResult
from .transcript_dto import MaskedSpan, Speaker, TranscriptEvent
from .transcript_ingest_dto import TranscriptIngestCommand
from .trigger_decision_dto import TriggerDecision

__all__ = [
    "CallDomain",
    "CallStartCommand",
    "CallStarted",
    "CallSummaryDraft",
    "Card",
    "ClosureCheckCommand",
    "ClosureType",
    "ClosureVerdict",
    "ComplianceCheckCommand",
    "ComplianceCheckResult",
    "ComplianceFinding",
    "DomainClassification",
    "FollowUpAction",
    "MaskedSpan",
    "MyselfQuery",
    "MyselfResult",
    "PostcallCommand",
    "RecommendCommand",
    "RecommendResult",
    "RecommendationCards",
    "RetrievedDoc",
    "SearchQuery",
    "SearchResult",
    "Source",
    "Speaker",
    "TranscriptEvent",
    "TranscriptIngestCommand",
    "TriggerDecision",
    "Verdict",
]
