# Requirement: E-3
"""프로파일대로 오류를 넣고, **넣은 뒤 실제 WER 을 잰다.**

「10% 주입」이라고 말하려면 결과가 정말 WER 0.10 인지 재야 한다. 편집 하나가 단어 오류를 몇 개
만드는지는 유형마다 다르다(띄어쓰기 병합은 2개, 끝 음절 탈락은 1개) — 그래서 **편집 수를 계산해서
넣지 않고, 말뭉치 WER 이 목표에 닿을 때까지 한 건씩 넣으며 잰다.** 돌려주는 `actual_wer` 가 곡선의
x 축이다. 목표값이 아니다.

**같은 시드면 같은 결과다** — `random.Random(seed)` 하나로만 뽑는다. 재측정 비교가 성립해야 한다.

⚠ **목표 수치를 여기 두지 않는다.** [6.1절](/docs/06/) 「오류 10% 구간 Recall@5 ≥0.60」은 판정선이지
주입기가 맞출 값이 아니다.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from ..metrics.asr import _edit_distance, normalize_hypothesis
from .hangul import compose, decompose, is_syllable
from .profile import JAMO_CONFUSIONS, MODELED_TYPES, OBSERVED_COUNTS, UNMODELED_SHARE

_DIGITS = re.compile(r"\d+")
_SINO = dict(zip("0123456789", ("공", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구")))

# 한 번에 넣는 편집이 목표를 크게 넘지 않도록, 도달 판정에 쓰는 여유. 넘친 만큼은 actual_wer 에 그대로 드러난다.
MAX_ATTEMPTS_PER_WORD = 20


@dataclass(frozen=True)
class InjectionResult:
    texts: tuple[str, ...]
    target_wer: float
    actual_wer: float  # 원문 대비 주입본의 말뭉치 WER — **곡선의 x 축은 이것이다**
    edits: dict[str, int]  # 유형별로 실제 넣은 건수
    seed: int
    reached: bool  # 목표에 닿았는가. 넣을 자리가 모자라면 False — 그 점은 곡선에서 빼거나 따로 표시한다
    unmodeled_share: float = UNMODELED_SHARE


def _verbalize_digits(word: str) -> str | None:
    """숫자열을 자릿수 읽기(공일공)로 바꾼다. 실측 쌍의 「1번씩→한 번씩」과 [2.4절](/docs/02/)의
    「구분자 없이 숫자를 한글로 읽는」 실패 모드를 함께 따른다. ⚠ 고유어 수사(한·두)는 실측 1쌍뿐이라 넣지 않는다."""
    if not _DIGITS.search(word):
        return None
    return _DIGITS.sub(lambda m: "".join(_SINO[d] for d in m.group(0)), word)


def _apply(kind: str, words: list[str], rng: random.Random) -> list[str] | None:
    """편집 하나. 넣을 자리가 없으면 None."""
    if kind == "spacing_merge":
        if len(words) < 2:
            return None
        i = rng.randrange(len(words) - 1)
        return words[:i] + [words[i] + words[i + 1]] + words[i + 2:]
    if kind == "spacing_split":
        cands = [i for i, w in enumerate(words) if len(w) >= 3]
        if not cands:
            return None
        i = rng.choice(cands)
        cut = rng.randrange(1, len(words[i]) - 1)
        return words[:i] + [words[i][:cut], words[i][cut:]] + words[i + 1:]
    if kind == "word_delete":
        if len(words) < 2:  # 발화를 통째로 지우지 않는다 — 그건 WER 이 아니라 누락이다
            return None
        i = rng.randrange(len(words))
        return words[:i] + words[i + 1:]
    if kind == "number_verbalize":
        cands = [i for i, w in enumerate(words) if _DIGITS.search(w)]
        if not cands:
            return None
        i = rng.choice(cands)
        return words[:i] + [_verbalize_digits(words[i])] + words[i + 1:]
    if kind == "ending_drop":
        cands = [i for i, w in enumerate(words) if len(w) >= 3 and is_syllable(w[-1])]
        if not cands:
            return None
        i = rng.choice(cands)
        return words[:i] + [words[i][:-1]] + words[i + 1:]
    if kind == "jamo_sub":
        return _jamo_sub(words, rng)
    raise ValueError(f"주입기가 흉내 내지 않는 유형이다: {kind}")


def _jamo_sub(words: list[str], rng: random.Random) -> list[str] | None:
    """실측 혼동표 안에서만 바꾼다. 표 밖의 혼동을 만들면 오타 주입이 된다."""
    slot_index = {"cho": 0, "jung": 1, "jong": 2}
    cands = []  # (단어 i, 글자 j, 혼동, 건수)
    for i, w in enumerate(words):
        for j, ch in enumerate(w):
            if not is_syllable(ch):
                continue
            parts = decompose(ch)
            for key, n in JAMO_CONFUSIONS.items():
                slot, src, _ = key
                if parts[slot_index[slot]] == src:
                    cands.append((i, j, key, n))
    if not cands:
        return None
    i, j, (slot, _, dst), _ = rng.choices(cands, weights=[c[3] for c in cands])[0]
    parts = list(decompose(words[i][j]))
    parts[slot_index[slot]] = dst
    new_word = words[i][:j] + compose(*parts) + words[i][j + 1:]
    return words[:i] + [new_word] + words[i + 1:]


def _errors(reference: str, hypothesis_words: list[str]) -> int:
    return _edit_distance(normalize_hypothesis(reference).split(), normalize_hypothesis(" ".join(hypothesis_words)).split())


def corpus_wer(references: list[str], hypotheses: list[str]) -> float:
    """채점기(`metrics/asr.score_pairs`)와 같은 기준 — 양쪽을 정규화한 뒤 오류 합 / 단어 합."""
    errors = sum(_errors(r, h.split()) for r, h in zip(references, hypotheses))
    total = sum(len(normalize_hypothesis(r).split()) for r in references)
    return errors / total if total else float("nan")


def inject(texts: list[str], target_wer: float, seed: int) -> InjectionResult:
    """말뭉치 WER 이 `target_wer` 에 닿을 때까지 프로파일 비율로 편집을 넣는다.

    **편집은 원문 토큰에 넣고, WER 만 정규화해서 잰다.** 첫 판은 입력을 정규화한 뒤 돌려줘서 오류율 0% 에서도
    `010-2345-6789` 의 하이픈이 사라졌다(2026-09-14) — C-5 곡선의 주 실패 모드가 「구분자 부재」라
    0% 지점부터 교란이 들어간다. 정규화는 채점기(`metrics/asr.py`)와 같은 기준으로 **재는 데만** 쓴다.

    ⚠ 자모 혼동은 **문맥 없이** 적용된다 — 실측 표에 있는 혼동이라도 「이곴」처럼 실제로 없는 음절이 나온다.
    """
    if not 0.0 <= target_wer < 1.0:
        raise ValueError("target_wer 는 0 이상 1 미만이다")
    rng = random.Random(seed)
    refs = list(texts)
    hyps = [t.split() for t in refs]
    total_words = sum(len(normalize_hypothesis(t).split()) for t in refs)
    kinds = list(MODELED_TYPES)
    weights = [OBSERVED_COUNTS[k] for k in kinds]
    edits = {k: 0 for k in kinds}
    errors = [0] * len(refs)

    attempts = 0
    while total_words and sum(errors) / total_words < target_wer:
        attempts += 1
        if attempts > MAX_ATTEMPTS_PER_WORD * total_words:
            break
        u = rng.choices(range(len(refs)), weights=[max(len(h), 1) for h in hyps])[0]
        kind = rng.choices(kinds, weights=weights)[0]
        new = _apply(kind, hyps[u], rng)
        if new is None:
            continue
        hyps[u] = new
        errors[u] = _errors(refs[u], new)
        edits[kind] += 1

    out = tuple(" ".join(h) for h in hyps)
    actual = corpus_wer(refs, list(out)) if total_words else float("nan")
    return InjectionResult(
        texts=out, target_wer=target_wer, actual_wer=actual, edits=edits, seed=seed,
        reached=bool(total_words) and actual >= target_wer,
    )
