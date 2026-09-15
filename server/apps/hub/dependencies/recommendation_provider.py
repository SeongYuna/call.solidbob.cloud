# Requirement: B-0, B-1, B-2, B-3, B-4, B-5, B-6
from __future__ import annotations

from fastapi import Depends

from hub.app.ports.input.recommendation_use_case import RecommendationUseCase
from hub.app.ports.output.domain_routing_port import DomainRoutingPort
from hub.app.ports.output.generation_port import GenerationPort
from hub.app.ports.output.recommendation_record_port import RecommendationRecordPort
from hub.app.ports.output.retrieval_port import RetrievalPort
from hub.app.ports.output.trigger_port import TriggerPort
from hub.app.use_cases.recommendation_interactor import RecommendationInteractor
from hub.dependencies.domain_routing_provider import get_domain_routing_port
from hub.dependencies.generation_provider import get_generation_port
from hub.dependencies.recommendation_record_provider import get_recommendation_record_port
from hub.dependencies.retrieval_provider import get_retrieval_port
from hub.dependencies.trigger_provider import get_trigger_port


def get_recommendation_use_case(
    trigger: TriggerPort = Depends(get_trigger_port),
    retrieval: RetrievalPort = Depends(get_retrieval_port),
    generation: GenerationPort = Depends(get_generation_port),
    domain_routing: DomainRoutingPort | None = Depends(get_domain_routing_port),
    record: RecommendationRecordPort = Depends(get_recommendation_record_port),
) -> RecommendationUseCase:
    return RecommendationInteractor(
        trigger=trigger, retrieval=retrieval, generation=generation, domain_routing=domain_routing, record=record
    )
