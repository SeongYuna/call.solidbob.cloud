# Requirement: B-1, F-2, QUA-1
"""저장 실패 정책(`decisions/318`) — 화면에 나가는 판정은 기록 실패(우리 쪽 DB 흔들림)로 사라지지 않는다.

- 추천: 카드는 나가고 `card_id` 만 None(카드 피드백만 못 남긴다) · 경고 로그
- 필요서류 자동 판정 · 체크리스트 판정: 판정은 나가고 경고 로그
- 통화가 없는 것(호출자 실수)은 삼키지 않는다 — `CallNotStartedError` 그대로(라우터가 404)
"""

import asyncio
import logging

import pytest

from hub.app.dtos.closure_dto import ClosureCheckCommand
from hub.app.dtos.recommendation_dto import RecommendCommand
from hub.app.dtos.required_docs_detection_dto import RequiredDocsDetectionCommand
from hub.app.ports.output.closure_record_port import ClosureRecordPort
from hub.app.ports.output.recommendation_record_port import RecommendationRecordPort
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError
from hub.app.use_cases.closure_check_interactor import ClosureCheckInteractor
from hub.app.use_cases.recommendation_interactor import RecommendationInteractor
from hub.app.use_cases.required_docs_detection_interactor import RequiredDocsDetectionInteractor

from .test_recommendation_interactor import EVENT, _Generation, _Retrieval, _Trigger
from .test_required_docs_detection_interactor import _Detect, _Gate


class _Flaky(RecommendationRecordPort, ClosureRecordPort):
    """DB 가 흔들린 저장소 — 또는 통화가 없는 저장소."""

    def __init__(self, exc):
        self.exc = exc

    async def record(self, _):
        raise self.exc


def _recommend(exc):
    it = RecommendationInteractor(trigger=_Trigger(), retrieval=_Retrieval(), generation=_Generation(), record=_Flaky(exc))
    return asyncio.run(it.recommend(RecommendCommand(event=EVENT)))


def _required_docs(exc):
    it = RequiredDocsDetectionInteractor(_Detect(), _Gate(), _Flaky(exc))
    return asyncio.run(it.check(RequiredDocsDetectionCommand(call_id="c1", procedure="DASAN-TERM-4.4", agent_utterances=("x",))))


def _closure(exc):
    it = ClosureCheckInteractor(_Gate(), _Flaky(exc))
    return asyncio.run(it.check(ClosureCheckCommand(call_id="c1", procedure="DASAN-TERM-4.4", evidence={"신고서": True})))


def test_추천_기록이_실패해도_카드는_나가고_card_id만_비는다(caplog):
    with caplog.at_level(logging.WARNING):
        result = _recommend(ConnectionError("db down"))
    assert result.fired and len(result.cards.cards) == 1
    assert all(c.card_id is None for c in result.cards.cards)
    assert "recommendation not stored" in caplog.text and "ConnectionError" in caplog.text
    assert "db down" not in caplog.text  # 예외 메시지(접속 정보가 들어갈 수 있다)는 싣지 않는다 — 타입 이름만


@pytest.mark.parametrize("run", [_required_docs, _closure], ids=["required_docs", "closure_check"])
def test_판정_기록이_실패해도_판정은_나간다(run, caplog):
    with caplog.at_level(logging.WARNING):
        verdict = run(ConnectionError("db down"))
    assert verdict.verdict == "incomplete"
    assert "closure verdict not stored" in caplog.text


@pytest.mark.parametrize("run", [_recommend, _required_docs, _closure], ids=["recommend", "required_docs", "closure_check"])
def test_통화가_없는_것은_삼키지_않는다(run):
    with pytest.raises(CallNotStartedError):
        run(CallNotStartedError("c1"))
