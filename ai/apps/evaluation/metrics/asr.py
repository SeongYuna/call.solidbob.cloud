# Requirement: A-5, E-1
"""STT 전사 정확도 — WER / CER. 규칙으로만 계산한다(LLM 채점 배제, 6.2절 원칙 1).

A-5(동시 통번역)의 1차 범위가 「서툰 한국어를 정확히 전사」이므로, 그것이 되는지 안 되는지를
말하려면 **정답 전사가 붙은 음성**과 이 채점기가 필요하다(`w3-a5-translation-spike`).

**평균 하나로 뭉개지 않는다.** 티켓이 명시적으로 요구한다 — 숙련도 등급별·조건별로 따로
내고, `aggregate_by_group()` 이 그것을 강제한다. 전체 평균만 적으면 "어느 등급에서 무너지는가"
가 사라지고, 그게 A-5 를 코어에 둘지 판단하는 근거의 전부다.

## AI Hub 라벨 표기를 어떻게 다루는가

AI Hub 음성 라벨은 전사 규약을 갖고 있다 — `(A-4)/(에이 다시 사)` 는 **철자 전사 / 발음
전사**를 함께 적은 것이고, `n/` 는 잡음 표시다. 정규화하지 않고 그대로 채점하면 STT 가
무엇을 뱉든 전부 오류가 된다. `normalize_reference()` 가 **철자 전사 쪽을 남긴다** —
STT 출력이 그쪽에 가깝고, 무엇보다 **한쪽을 고른 사실이 기록에 남아야** 나중에 수치를
비교할 수 있기 때문이다.

⚠ 정규화는 점수를 올리는 조치다. 어느 규칙을 적용했는지 `NORMALIZATION_RULES` 로 드러내
두었고, 수치를 인용할 때 함께 밝힌다(절대 원칙 10).
"""

from __future__ import annotations

import re
import unicodedata

# 적용한 정규화 — 수치와 함께 인용한다.
NORMALIZATION_RULES = (
    "이중 전사 `(철자)/(발음)` → 철자 쪽만 남긴다",
    "잡음·간투어 표시 `n/` `b/` `l/` `o/` `u/` 제거",
    "괄호 안 화자 주석 제거",
    "문장부호 제거 — 하이픈은 공백 없이 지운다(`A-4` → `A4`)",
    "유니코드 NFC 정규화 + 공백 1칸으로 축약",
)

# `(A-4)/(에이 다시 사)` — 앞이 철자, 뒤가 발음. 앞을 남긴다.
_DUAL = re.compile(r"\(([^()]*)\)\s*/\s*\(([^()]*)\)")
# 잡음·간투어 표시. AI Hub 규약상 토큰 앞에 한 글자 + `/` 로 붙는다.
_TAG = re.compile(r"(?:^|\s)[nbluo]/\s*")
# 공백으로 바꿀 문장부호와 **그냥 지울** 문장부호를 나눈다. `A-4` 를 `A 4` 로 만들면
# 토큰이 하나 늘어 WER 분모가 부풀고, 정답과 가설의 띄어쓰기가 다를 때 오류가 두 배로 잡힌다.
_PUNCT_TO_SPACE = re.compile(r"[.,!?~…\"'`·:;—\[\]{}<>]")
_PUNCT_TO_DROP = re.compile(r"[-]")
_SPACES = re.compile(r"\s+")


def normalize_reference(text: str) -> str:
    """AI Hub 라벨 → 채점용 문자열."""
    text = _DUAL.sub(lambda m: m.group(1), text)
    text = _TAG.sub(" ", text)
    return normalize_hypothesis(text)


def normalize_hypothesis(text: str) -> str:
    """STT 출력 → 채점용 문자열. 정답 쪽과 **같은** 정리를 받아야 공정하다."""
    text = unicodedata.normalize("NFC", text or "")
    text = _PUNCT_TO_SPACE.sub(" ", text)
    text = _PUNCT_TO_DROP.sub("", text)
    return _SPACES.sub(" ", text).strip()


def _edit_distance(ref: list[str] | str, hyp: list[str] | str) -> int:
    """레벤슈타인 거리. 행 두 개만 들고 돈다 — 발화 하나가 길어도 메모리가 늘지 않는다."""
    if len(ref) < len(hyp):
        ref, hyp = hyp, ref
    previous = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, start=1):
        current = [i]
        for j, h in enumerate(hyp, start=1):
            current.append(min(
                previous[j] + 1,          # 삭제
                current[j - 1] + 1,       # 삽입
                previous[j - 1] + (r != h),  # 치환
            ))
        previous = current
    return previous[-1]


def word_error_rate(reference: str, hypothesis: str) -> float:
    """WER. 정답이 비어 있으면 nan — **0.0 으로 만들지 않는다**(절대 원칙 2)."""
    ref = normalize_reference(reference).split()
    hyp = normalize_hypothesis(hypothesis).split()
    if not ref:
        return float("nan")
    return _edit_distance(ref, hyp) / len(ref)


def char_error_rate(reference: str, hypothesis: str) -> float:
    """CER. 한국어는 띄어쓰기가 흔들려 WER 이 과하게 나온다 — 둘을 함께 본다."""
    ref = normalize_reference(reference).replace(" ", "")
    hyp = normalize_hypothesis(hypothesis).replace(" ", "")
    if not ref:
        return float("nan")
    return _edit_distance(ref, hyp) / len(ref)


def score_pairs(pairs: list[tuple[str, str]]) -> dict:
    """(정답, 가설) 목록 → WER/CER.

    **문장별 평균이 아니라 전체 오류 합 / 전체 길이 합**이다. 짧은 발화 하나가 WER 3.0 을
    찍으면 문장 평균은 그 한 건에 끌려간다 — 표준 ASR 채점이 이 방식을 쓰는 이유다.
    """
    scored = [(normalize_reference(r), normalize_hypothesis(h)) for r, h in pairs]
    scored = [(r, h) for r, h in scored if r]
    if not scored:
        return {"wer": float("nan"), "cer": float("nan"), "n": 0}

    w_err = sum(_edit_distance(r.split(), h.split()) for r, h in scored)
    w_len = sum(len(r.split()) for r, h in scored)
    c_err = sum(_edit_distance(r.replace(" ", ""), h.replace(" ", "")) for r, h in scored)
    c_len = sum(len(r.replace(" ", "")) for r, h in scored)
    return {
        "wer": w_err / w_len if w_len else float("nan"),
        "cer": c_err / c_len if c_len else float("nan"),
        "n": len(scored),
    }


def aggregate_by_group(
    rows: list[tuple[str, str, str]]
) -> dict[str, dict]:
    """(그룹, 정답, 가설) → 그룹별 WER/CER + 전체.

    **그룹을 나눠 내는 것이 이 함수의 존재 이유다.** A-5 티켓이 *"전체 평균 하나로
    뭉개지 않는다"* 를 완료 조건으로 걸었다 — 숙련도 등급별로 무너지는 지점이 다른데
    평균만 적으면 그 사실이 사라진다. 표본이 적은 그룹은 `n` 이 함께 나가므로
    수치를 인용할 때 그것을 보고 판단한다.
    """
    groups: dict[str, list[tuple[str, str]]] = {}
    for group, ref, hyp in rows:
        groups.setdefault(group, []).append((ref, hyp))
    result = {g: score_pairs(pairs) for g, pairs in sorted(groups.items())}
    result["__all__"] = score_pairs([(r, h) for _, r, h in rows])
    return result
