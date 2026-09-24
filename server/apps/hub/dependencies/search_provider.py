# Requirement: B-2, B-3, B-6
"""수동 검색이 쓸 검색 포트는 자동 추천과 **한 겹 다르다**(`_project/decisions/135`).

자동 추천은 대화 중 트리거가 부르고, 수동 검색은 상담원이 직접 친다. B-6 「관련 문서 없음」 문턱은
뒤쪽에만 건다 — 앞쪽에 걸었다가 대화체 발화의 60%가 기권해 보류한 것이 `decisions/215` 다.

그 갈림을 여기서 **자리로만** 만든다. 문턱 값도, 씌울지 말지도 `ai/` 가 정한다(`provider.wrap_no_answer`) —
허브는 스포크를 모른다. 아무도 안 꽂으면 자동 추천과 같은 포트를 쓴다(오늘까지의 동작).
"""
from __future__ import annotations

from fastapi import Depends

from hub.app.ports.input.search_use_case import SearchUseCase
from hub.app.ports.output.retrieval_port import RetrievalPort
from hub.app.use_cases.search_interactor import SearchInteractor
from hub.dependencies.retrieval_provider import get_retrieval_port


def get_search_retrieval_port(retrieval: RetrievalPort = Depends(get_retrieval_port)) -> RetrievalPort:
    """수동 검색 전용 검색 포트. 합성 루트(`main.py`)가 기권을 씌운 것을 꽂는다."""
    return retrieval


def get_search_use_case(retrieval: RetrievalPort = Depends(get_search_retrieval_port)) -> SearchUseCase:
    return SearchInteractor(retrieval=retrieval)
