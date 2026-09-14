# Requirement: F-2
"""RequiredDocsDetectionPort 구현 — 도메인 키워드 판정(`domain/services/detection.py`)을 허브 포트로 옮긴다."""

from __future__ import annotations

from hub.app.ports.output.required_docs_detection_port import RequiredDocsDetectionPort

from ...domain.services.detection import informed_documents
from ...domain.services.gate import rule_for


class KeywordRequiredDocsDetectionAdapter(RequiredDocsDetectionPort):
    def detect(self, procedure: str, agent_utterances: tuple[str, ...]) -> dict[str, bool]:
        return informed_documents(rule_for(procedure), list(agent_utterances))
