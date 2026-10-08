# Requirement: D-1, D-2, D-3
"""PostcallPort 프로바이더. 2026-09-15 부터 규칙 발췌 초안이 기본이다 (`decisions/306`).

그 전까지는 501 이었다 — 빈 문자열이나 "요약 없음"을 돌려주면 화면에는 **요약이 생성됐는데 내용이
없는 것**으로 보여, 모듈이 없는 상태와 구분되지 않기 때문이었다(절대 원칙 10). 지금 구현은 빈 요약을
만들지 않는다 — 발췌할 발화가 없어도 발화 건수는 싣는다.

**요약을 «쓰지» 않고 자막에서 «고른다».** LLM 요약이 운영에 올라오면 이 프로바이더만 바꾼다.
"""

from __future__ import annotations

from fastapi import Depends, Request
from postcall.adapter.outbound.rule_postcall_adapter import RulePostcallAdapter

from hub.app.ports.input.postcall_use_case import PostcallUseCase
from hub.adapter.outbound.postgres.compliance_flag_repository import PostgresComplianceFlagRepository
from hub.adapter.outbound.postgres.connection import build_connection_factory
from hub.app.ports.output.compliance_flag_query_port import ComplianceFlagQueryPort
from hub.app.ports.output.masking_port import MaskingPort
from hub.app.ports.output.postcall_port import PostcallPort
from hub.app.ports.output.postcall_record_port import PostcallRecordPort
from hub.app.use_cases.postcall_interactor import PostcallInteractor
from hub.dependencies.masking_provider import get_masking_port
from hub.dependencies.postcall_record_provider import get_postcall_record_port


def get_postcall_port() -> PostcallPort:
    return RulePostcallAdapter()


def get_compliance_flag_query_port(request: Request) -> ComplianceFlagQueryPort | None:
    """위반 발화 번호 조회 — PostgreSQL 이 없으면 None(요약은 전처럼 만든다)."""
    settings = request.app.state.settings
    if not settings.postgres_configured:
        return None
    return PostgresComplianceFlagRepository(build_connection_factory(settings))


def get_postcall_use_case(
    postcall: PostcallPort = Depends(get_postcall_port),
    record: PostcallRecordPort = Depends(get_postcall_record_port),
    flags: ComplianceFlagQueryPort | None = Depends(get_compliance_flag_query_port),
    # 화면 자막이 원문일 수 있다(`decisions/326`) — 전사 수신과 같은 마스킹(NER 이 꽂히면 그것까지)으로 가린다
    masking: MaskingPort = Depends(get_masking_port),
) -> PostcallUseCase:
    return PostcallInteractor(postcall=postcall, record=record, masking=masking, flags=flags)
