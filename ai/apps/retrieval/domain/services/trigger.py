# Requirement: B-1
"""트리거 판정 규칙 v1 — 순수 계산이라 domain 계층에 둔다.

**언제 검색을 발동할 것인가.** 3주차 v1 은 자체 침묵 타이머 대신 **Google STT 의 `is_final`
도착 기반**이다(2026-08-25 팀 컨펌, 정성윤 제안). 침묵 임계값을 우리가 재려면 발화 간 침묵
길이를 잴 데이터가 필요한데 보유 데이터로는 잴 수 없었다 — 그래서 STT 가 이미 하고 있는
엔드포인팅 판단을 그대로 쓴다.

허용 창은 발화 종료 후 **0~1,500ms** 다([4.1절](/docs/04/), `_project/decisions/001`).
그 창 안에 들어가는지 판정하는 쪽은 `evaluation/metrics/trigger.py` 이고, 여기는 발동
여부와 시각만 정한다 — **판정 규칙과 채점 규칙을 한 파일에 두지 않는다.**
"""

from __future__ import annotations

# V4 실측: Google STT 최종 결과가 발화 종료 **+346ms** 에 도착했다
# (`jekyll/docs/05-데이터확보계획.markdown`, 2026-08-25).
#
# ⚠ 이 값은 **모형이지 측정이 아니다.** 포트 시그니처(`decide(event)`)에 이벤트 도착 시각이
#   없어서, 발동 시각을 "발화 종료 + 이 상수"로 놓는 것 말고 할 수 있는 게 없다.
#   실시간 경로는 콜 미디에이터 도착 시각(`received_at_ms`)으로 대체한다(2026-09-14) — 그게 없을 때 이 상수로 계산한
#   지연 분포는 **전부 이 값 하나로 수렴**한다(p50 = p95 = 346). 그래서 평가 하네스에는
#   트리거 포트를 꽂지 않는다(`scripts/run_eval.py` 주석 참고, 절대 원칙 10).
STT_FINAL_LAG_MS = 346


def should_fire(*, is_final: bool, speaker: str, text: str) -> bool:
    """이 전사 이벤트에서 검색을 발동하는가.

    셋 다 만족해야 한다:

    1. **`is_final` 이다.** interim 은 20초 발화에 199건(V4 실측) 온다 — 매번 발동하면
       검색이 초당 수십 번 돈다.
    2. **고객 발화다.** 상담원이 말하는 중에 상담원 화면을 바꾸면 방해가 된다.
       문서가 필요한 시점은 **고객이 질문을 끝냈을 때**다.
    3. **내용이 있다.** 빈 문자열로 검색하면 아무 의미 없는 상위 문서가 뜬다.
    """
    return is_final and speaker == "customer" and bool(text.strip())


def fire_at_ms(utterance_end_ms: int | None, *, lag_ms: int = STT_FINAL_LAG_MS) -> int | None:
    """발동 시각(통화 기준 ms). 발화 종료 시각을 모르면 None 이다.

    **이건 모형값이다** — 위 `STT_FINAL_LAG_MS` 주석 참고. 실제 도착 시각이 포트로 들어오면
    그 값을 그대로 쓰는 쪽으로 바꾼다.
    """
    if utterance_end_ms is None:
        return None
    return utterance_end_ms + lag_ms
