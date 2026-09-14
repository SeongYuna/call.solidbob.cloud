# Requirement: D-5
"""D-5 판정 결과를 hub 기록 포트(`VoiceOutlierRecordPort`)로 넘긴다.

여기가 adapter 인 이유: hub 의 DTO·포트를 아는 코드이기 때문이다. 판정은
`domain/services/outlier.py` 에 있고 이 파일은 형태를 바꿔 넘기기만 한다(`.importlinter` 계약 1).

⚠ **아직 이것을 부르는 실시간 경로가 없다(2026-09-14).** 톤 특징값은 오디오에서 나오는데
`server/` 는 텍스트만 받는다 — 게이트웨이가 발화별 특징값을 보내거나, `server` 가 오디오를 받는
경로가 생겨야 한다. 지금은 **저장 경로까지만** 만들어 뒀다. 저장이 없으면 그 경로가 생겨도
통화가 끝나는 순간 결과가 사라지기 때문이다(오디오를 보관하지 않는다, 절대 원칙 7).
"""

from __future__ import annotations

from hub.app.dtos.transcript_dto import Speaker
from hub.app.dtos.voice_outlier_dto import VoiceOutlier
from hub.app.ports.output.voice_outlier_record_port import VoiceOutlierRecordPort

from ...domain.services.outlier import segment_outliers


async def record_speaker_temperature(
    record: VoiceOutlierRecordPort,
    call_id: str,
    speaker: Speaker,
    samples: list[tuple[int, float]],
) -> bool:
    """한 화자의 발화별 특징값을 판정해 저장한다. **저장했으면 True, 판정하지 않았으면 False.**

    기준선을 못 만들면(발화 8건 미만 등) **포트를 부르지 않는다** — 빈 목록으로 갈아끼우면
    「튄 구간 없음」으로 기록되고, 그전에 남은 판정까지 지운다.
    """
    result = segment_outliers(speaker, samples)
    if not result.baseline_usable:
        return False
    await record.replace(
        call_id,
        speaker,
        [
            VoiceOutlier(segment_id=o.segment_id, speaker=speaker, robust_z=o.robust_z, baseline_n=o.baseline_n)
            for o in result.outliers
        ],
    )
    return True
