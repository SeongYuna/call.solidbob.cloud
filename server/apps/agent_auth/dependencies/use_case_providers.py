# Requirement: J-1
from __future__ import annotations

from fastapi import Depends

from agent_auth.app.ports.input.agent_token_list_use_case import AgentTokenListUseCase
from agent_auth.app.ports.input.current_agent_use_case import CurrentAgentUseCase
from agent_auth.app.ports.input.issue_agent_token_use_case import IssueAgentTokenUseCase
from agent_auth.app.ports.input.revoke_agent_token_use_case import RevokeAgentTokenUseCase
from agent_auth.app.ports.output.agent_token_port import AgentTokenPort
from agent_auth.app.use_cases.agent_token_list_interactor import AgentTokenListInteractor
from agent_auth.app.use_cases.current_agent_interactor import CurrentAgentInteractor
from agent_auth.app.use_cases.issue_agent_token_interactor import IssueAgentTokenInteractor
from agent_auth.app.use_cases.revoke_agent_token_interactor import RevokeAgentTokenInteractor
from agent_auth.dependencies.providers import get_agent_token_port


def get_issue_agent_token_use_case(tokens: AgentTokenPort = Depends(get_agent_token_port)) -> IssueAgentTokenUseCase:
    return IssueAgentTokenInteractor(tokens)


def get_current_agent_use_case(tokens: AgentTokenPort = Depends(get_agent_token_port)) -> CurrentAgentUseCase:
    return CurrentAgentInteractor(tokens)


def get_agent_token_list_use_case(tokens: AgentTokenPort = Depends(get_agent_token_port)) -> AgentTokenListUseCase:
    return AgentTokenListInteractor(tokens)


def get_revoke_agent_token_use_case(tokens: AgentTokenPort = Depends(get_agent_token_port)) -> RevokeAgentTokenUseCase:
    return RevokeAgentTokenInteractor(tokens)
