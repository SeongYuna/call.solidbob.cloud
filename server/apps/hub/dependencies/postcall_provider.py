# Requirement: D-1, D-2, D-3
"""PostcallPort 프로바이더. 2026-09-15 부터 규칙 발췌 초안이 기본이다 (`decisions/306`).

그 전까지는 501 이었다 — 빈 문자열이나 "요약 없음"을 돌려주면 화면에는 **요약이 생성됐는데 내용이
없는 것**으로 보여, 모듈이 없는 상태와 구분되지 않기 때문이었다(절대 원칙 10). 지금 구현은 빈 요약을
만들지 않는다 — 발췌할 발화가 없어도 발화 건수는 싣는다.

**요약을 «쓰지» 않고 자막에서 «고른다».** LLM 요약이 운영에 올라오면 이 프로바이더만 바꾼다.
"""

from __future__ import annotations

from fastapi import Depends
from postcall.adapter.outbound.rule_postcall_adapter import RulePostcallAdapter

from hub.app.ports.input.postcall_use_case import PostcallUseCase
from hub.app.ports.output.postcall_port import PostcallPort
from hub.app.use_cases.postcall_interactor import PostcallInteractor


def get_postcall_port() -> PostcallPort:
    return RulePostcallAdapter()


def get_postcall_use_case(postcall: PostcallPort = Depends(get_postcall_port)) -> PostcallUseCase:
    return PostcallInteractor(postcall=postcall)
