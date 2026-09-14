# Requirement: E-3, QUA-1
"""STT 오류 주입기 — 티켓 완료 조건 중 **곡선 측정 전까지의 셋**을 고정한다.
① 유형이 실측에서 왔다 ② 같은 시드면 같은 결과 ③ 주입 후 WER 을 재서 목표와 맞는지 본다."""

from __future__ import annotations

import random

import pytest

from evaluation.error_injection.classify import TYPES, EditProfile, accumulate, classify_span
from evaluation.error_injection.hangul import compose, decompose
from evaluation.error_injection.injector import _apply, _jamo_sub, corpus_wer, inject
from evaluation.error_injection.profile import (
    JAMO_CONFUSIONS,
    MODELED_TYPES,
    OBSERVED_COUNTS,
    UNMODELED_SHARE,
)
from evaluation.golden_set import load_golden_set
from evaluation.metrics.asr import score_pairs


def _corpus() -> list[str]:
    """골든셋 고객 발화 — 곡선을 낼 때 쓸 말뭉치와 같다."""
    return [it.customer_utterance for it in load_golden_set() if it.customer_utterance]


# ── 한글 자모 ─────────────────────────────────────────────────────────
def test_음절을_분해했다가_다시_합치면_같다():
    for ch in ("가", "뜨", "맞", "있", "힣"):
        assert compose(*decompose(ch)) == ch


# ── ① 유형은 실측 분류 규칙에서 온다 ─────────────────────────────────────
@pytest.mark.parametrize(
    "a, b, kind",
    [
        ("해주세요", "해 주세요", "spacing_split"),
        ("입국 제한", "입국제한", "spacing_merge"),
        ("발급", "", "word_delete"),  # difflib 이 넘기는 삭제 구간 그대로
        ("2번 창구", "이 번 창구", "number_verbalize"),
        ("파리바게트", "파리바게뜨", "jamo_sub"),
        ("같아서요", "같아서", "ending_drop"),
        ("등본 발급 문의요", "등산 가고 싶네", "unmodeled"),
    ],
)
def test_분류_규칙(a, b, kind):
    got, _ = classify_span(a.split(), b.split())
    assert got == kind


def test_숫자로_시작해도_뒤가_무너졌으면_수사_읽기로_세지_않는다():
    """첫 판이 이 경우를 number_verbalize 로 세서 흉내 낼 수 있는 몫이 부풀었다(2026-09-14)."""
    assert classify_span("1번 창구에서 서류를 내요".split(), "한번 써 보면 엄청 나네요".split())[0] == "unmodeled"


def test_프로파일은_분류_유형과_어긋나지_않는다():
    assert set(OBSERVED_COUNTS) == set(TYPES)
    assert set(MODELED_TYPES) <= set(TYPES) and all(OBSERVED_COUNTS[t] > 0 for t in MODELED_TYPES)
    assert 0 < UNMODELED_SHARE < 1  # 흉내 내지 못하는 몫이 있다는 사실을 지우지 않는다


def test_누적은_편집_구간과_정답_단어를_센다():
    p = EditProfile()
    accumulate(p, "여권 재발급 서류 알려주세요", "여권 재발급 서류 알려 주세요")
    assert (p.pairs, p.reference_words, p.counts["spacing_split"]) == (1, 4, 1)


# ── 편집 하나하나 ──────────────────────────────────────────────────────
def test_자모_치환은_실측_혼동표_안에서만_일어난다():
    rng = random.Random(0)
    for _ in range(200):
        words = ["사업자등록증", "떼러", "왔어요"]
        new = _jamo_sub(words, rng)
        if new is None:
            continue
        changed = [(a, b) for w, v in zip(words, new) for a, b in zip(w, v) if a != b]
        assert len(changed) == 1
        (a, b), = changed
        diffs = [(s, x, y) for s, x, y in zip(("cho", "jung", "jong"), decompose(a), decompose(b)) if x != y]
        assert len(diffs) == 1 and diffs[0] in JAMO_CONFUSIONS


def test_숫자는_자릿수로_읽는다():
    assert _apply("number_verbalize", ["010", "번호"], random.Random(0)) == ["공일공", "번호"]


def test_한_단어_발화는_통째로_지우지_않는다():
    assert _apply("word_delete", ["네"], random.Random(0)) is None


# ── ② 같은 시드면 같은 결과 ─────────────────────────────────────────────
def test_같은_시드면_같은_결과_다른_시드면_다른_결과():
    texts = _corpus()
    a, b, c = inject(texts, 0.10, seed=7), inject(texts, 0.10, seed=7), inject(texts, 0.10, seed=8)
    assert a == b
    assert a.texts != c.texts


# ── ③ 목표와 실제를 잰다 ────────────────────────────────────────────────
@pytest.mark.parametrize("target", [0.05, 0.10, 0.15, 0.20])
def test_주입_후_실제_WER_이_목표에_닿고_크게_넘지_않는다(target):
    texts = _corpus()
    result = inject(texts, target, seed=20260914)
    assert result.reached
    assert target <= result.actual_wer < target + 0.01  # 한 건씩 넣으며 재므로 넘쳐도 편집 1건 몫이다
    # 채점기(metrics/asr.py)로 다시 재도 같은 값 — x 축이 채점 기준과 같다
    assert score_pairs(list(zip(texts, result.texts)))["wer"] == pytest.approx(result.actual_wer)
    assert sum(result.edits.values()) > 0


def test_오류율_0_이면_아무것도_바꾸지_않는다():
    texts = _corpus()
    result = inject(texts, 0.0, seed=1)
    assert result.actual_wer == 0.0 and sum(result.edits.values()) == 0
    assert list(result.texts) == [" ".join(t.split()) for t in texts]


def test_구분자와_문장부호를_지우지_않는다():
    """C-5 곡선의 주 실패 모드가 「구분자 부재」다 — 주입기가 0% 에서 이미 하이픈을 지우면 곡선 전체가 교란된다."""
    text = "번호는 010-2345-6789예요, 다시 연락 주세요?"
    result = inject([text], 0.0, seed=1)
    assert result.texts == (text,)
    assert corpus_wer([text], [text]) == 0.0


def test_넣을_자리가_모자라면_닿지_못했다고_말한다():
    result = inject(["OK"], 0.5, seed=1)  # 한글·숫자가 없는 한 단어 — 어떤 편집도 들어갈 자리가 없다
    assert result.reached is False
