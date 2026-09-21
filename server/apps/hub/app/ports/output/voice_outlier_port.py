# Requirement: D-5
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from hub.app.dtos.transcript_dto import Speaker
from hub.app.dtos.voice_outlier_dto import VoiceOutlierVerdict


class VoiceOutlierPort(ABC):
    """D-5 통화 온도 — 한 화자의 발화별 음성에서 **그 화자 자신의 기준선 대비** 튄 발화를 고른다
    (`_project/decisions/203`). 판정은 규칙(중앙값·MAD 로버스트 z)이고 학습 모델이 없다(절대 원칙 9).

    `VoiceOutlierRecordPort`(기록)와 짝이다 — `CallGuardPort`(판정) ↔ `CallGuardFlagRecordPort`(기록)와
    같은 나눔. **평가 하네스가 꽂는 접점이 이 포트다**(`docs/architecture.md §1` — 평가 전용 Protocol 을
    따로 두지 않는다).

    입력은 `(segment_id, 오디오 파일 경로)` 목록이다. 특징값이 아니라 **오디오**를 받는 이유: 골든셋은
    라벨(튀어야 할 발화·차분한 발화)과 원본 음성만 담아야 정답으로 남는다 — 우리 추출기가 낸 특징값을
    골든셋에 적어 두면 추출기를 고칠 때마다 정답이 낡고, 무엇보다 추출기(옥타브 오류가 실제로 있었다,
    `w3-call-temperature`)가 채점 범위 밖으로 빠진다. 파일을 읽는 I/O 포트라 async 다(`UploadStoragePort` 와 같은 이유).
    오디오는 저작권·개인정보가 해결된 출처(AI Hub·다산콜DB)뿐이다(절대 원칙 7).

    ⚠ **기준선을 못 만들면(발화 8건 미만 등) `judged=False` 로 돌려준다** — 빈 `outliers` 는 「튄 구간 없음」이
    아니라 「판정하지 않았다」다(절대 원칙 10). 부르는 쪽이 둘을 구분해 센다.
    """

    @abstractmethod
    async def judge(
        self, call_id: str, speaker: Speaker, utterances: Sequence[tuple[int, str]]
    ) -> VoiceOutlierVerdict: ...
