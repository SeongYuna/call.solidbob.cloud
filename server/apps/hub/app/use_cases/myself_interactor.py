# Requirement: 부록 A-1
"""허브 자기소개 — 실제 기능만 말한다. 부록 A-1: "안전합니다"·"위험도 N%"·"완벽히 차단" 류 표현 금지,
하지 않는 것을 먼저 명시."""

from __future__ import annotations

from hub.app.dtos.myself_dto import MyselfQuery, MyselfResult
from hub.app.ports.input.myself_use_case import MyselfUseCase
from hub.app.ports.output.myself_record_port import MyselfRecordPort

_ENDPOINTS = (
    "GET /hub/myself — 이 자기소개",
    "POST /hub/calls — 게이트웨이가 통화 시작을 알린다. 전사보다 먼저 와야 한다(transcript_segment → call 외래키)",
    "POST /hub/transcripts — 게이트웨이가 보낸 전사 1건을 받아 C-5 마스킹을 거친 전사 이벤트(7.3절 계약)로 돌려준다",
)
_DOES_NOT = (
    "마스킹·트리거·검색·생성·컴플라이언스·종결 판정을 직접 하지 않는다 — 각 스포크가 구현한 포트를 부를 뿐이다",
    "종결 가능 여부나 마스킹 대상을 생성 모델로 판정하지 않는다 (절대 원칙 9)",
    "마스킹 전 원문을 저장·로그·다른 스포크에 넘기지 않는다 (SEC-1)",
    "정의된 P1~P5 패턴 밖의 개인정보 탐지를 보장하지 않는다 (5.5절 한계)",
)


class MyselfInteractor(MyselfUseCase):
    def __init__(self, record: MyselfRecordPort) -> None:
        self._record = record

    async def introduce_myself(self, query: MyselfQuery) -> MyselfResult:
        await self._record.record(query)
        return MyselfResult(
            name=query.name,
            introduction=(
                "CallGuard FastAPI 코어의 허브. 7.3절 인터페이스 계약 3종(전사 이벤트·추천 카드·종결 판정)을 "
                "DTO 와 포트로 소유하고, 스포크(마스킹·검색·생성·컴플라이언스·종결 게이트)를 포트로 배선한다. "
                "현재 등록된 스포크 구현체는 dependencies/ 프로바이더가 알려준다."
            ),
            endpoints=_ENDPOINTS,
            does_not=_DOES_NOT,
        )
