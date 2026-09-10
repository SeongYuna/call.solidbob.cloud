# Requirement: 7.3절 인터페이스 계약, E-1
"""허브 아웃바운드 포트 — 허브가 스포크(또는 기록 장치)에 요구하는 계약. 스포크가 이 ABC 를 구현하고
dependencies/ 에서 결합한다. **이 포트들이 유일한 계약이다** — evaluation/harness.py 도 같은 포트로 채점한다
(스포크 하나에 계약이 둘이면 반드시 갈라진다).

호출자:
- MaskingPort ← hub.app.use_cases.transcript_ingest_interactor, evaluation.harness
- TriggerPort · RetrievalPort · DomainRoutingPort · GenerationPort · CompliancePort · ClosureGatePort ← evaluation.harness
  (파이프라인 슬라이스가 생기면 그 인터랙터도 호출자가 된다)
- *RecordPort ← 각 슬라이스 인터랙터
"""

from .call_start_record_port import CallStartRecordPort
from .card_feedback_port import CardFeedbackPort
from .closure_gate_port import ClosureGatePort
from .compliance_port import CompliancePort
from .domain_routing_port import DomainRoutingPort
from .generation_port import GenerationPort
from .knowledge_gap_port import KnowledgeGapPort
from .masking_port import MaskingPort
from .myself_record_port import MyselfRecordPort
from .postcall_port import PostcallPort
from .retrieval_port import RetrievalPort
from .transcript_ingest_record_port import TranscriptIngestRecordPort
from .transcript_query_port import TranscriptQueryPort
from .trigger_port import TriggerPort

__all__ = [
    "CallStartRecordPort",
    "CardFeedbackPort",
    "ClosureGatePort",
    "CompliancePort",
    "DomainRoutingPort",
    "GenerationPort",
    "KnowledgeGapPort",
    "MaskingPort",
    "MyselfRecordPort",
    "PostcallPort",
    "RetrievalPort",
    "TranscriptIngestRecordPort",
    "TranscriptQueryPort",
    "TriggerPort",
]
