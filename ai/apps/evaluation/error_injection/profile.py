# Requirement: E-3
"""실측 STT 오류 프로파일 — **여기 적힌 숫자는 전부 아래 명령의 출력이다. 손으로 고르지 않았다.**

    .venv/bin/python scripts/build_stt_error_profile.py        # 2026-09-14, 커밋 9970fba 기준 코드

출처: `data/processed/bandwidth-penalty/result.json` — `scripts/measure_bandwidth_penalty.py` 가
2026-09-09 에 저장한 **정답 전사 ↔ Chirp 출력** 20발화 × 2조건(16kHz 원본·8kHz) = 40쌍,
데이터 `aihub-krespspeech/validation`(내국인, 시드 20260909), 정답 단어 452, 편집 구간 81.
원문은 AI Hub 데이터라 저장소에 싣지 않는다 — 건수와 낱자 혼동표만 옮겼다.

## 반드시 함께 적을 한계

- **표본이 작다.** 편집 81건, 자모 혼동은 11종 17건이다. 혼동표에 없는 혼동은 주입하지 않는다 —
  실제 STT 가 더 다양하게 틀리므로 **이 표는 하한이다.**
- **두 조건이 독립이 아니다.** 같은 발화를 두 번 전사했다 — 대부분 같은 오류를 낸다.
- **흉내 내지 못하는 몫이 46.9%(38/81)다** — `unmodeled` 37(환청·의미 붕괴·여러 자모 치환) + `ending_add` 1.
  같은 WER 에서 주입 오류는 실제보다 덜 파괴적이다 → **곡선은 낙관 쪽으로 기운다.** 곡선 옆에 이 비율을 적는다.
- **내국인 낭독·질의 발화다.** 전화망(코덱·잡음)·외국인 화자·민원 대화의 오류 분포가 아니다.
"""

from __future__ import annotations

PROFILE_SOURCE = "bandwidth-penalty/result.json · 2026-09-09 · 40쌍 · 편집 81"

# classify.TYPES 별 건수 (__all__)
OBSERVED_COUNTS: dict[str, int] = {
    "spacing_merge": 2,
    "spacing_split": 12,
    "word_delete": 3,
    "word_insert": 0,
    "number_verbalize": 2,
    "jamo_sub": 17,
    "ending_drop": 7,
    "ending_add": 1,
    "unmodeled": 37,
}

# 주입기가 흉내 내는 유형. 나머지(word_insert·ending_add·unmodeled)는 **넣을 내용을 지어내야 해서** 뺀다.
MODELED_TYPES = ("spacing_merge", "spacing_split", "word_delete", "number_verbalize", "jamo_sub", "ending_drop")

UNMODELED_SHARE = sum(OBSERVED_COUNTS[t] for t in OBSERVED_COUNTS if t not in MODELED_TYPES) / sum(
    OBSERVED_COUNTS.values()
)

# (자리, 정답 자모, STT 자모) → 건수. 종성 "" 은 받침 없음.
JAMO_CONFUSIONS: dict[tuple[str, str, str], int] = {
    ("jong", "", "ㅆ"): 4,
    ("cho", "ㅅ", "ㅇ"): 4,
    ("cho", "ㅌ", "ㄸ"): 2,
    ("cho", "ㅇ", "ㅁ"): 2,
    ("jung", "ㅜ", "ㅗ"): 2,
    ("cho", "ㅂ", "ㄴ"): 2,
    ("jong", "ㅈ", "ㄴ"): 2,
    ("jung", "ㅓ", "ㅏ"): 1,
    ("jong", "ㅅ", ""): 1,
    ("jung", "ㅔ", "ㅐ"): 1,
    ("jung", "ㅓ", "ㅗ"): 1,
}
