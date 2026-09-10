# Requirement: A-5, E-1
"""WER/CER 채점기. **정규화 규칙이 점수를 만든다**는 점을 테스트로 드러내 둔다."""

from __future__ import annotations

import math

from evaluation.metrics.asr import (
    aggregate_by_group,
    char_error_rate,
    normalize_reference,
    score_pairs,
    word_error_rate,
)


# ── AI Hub 라벨 정규화 ──────────────────────────────────────────────────
def test_이중_전사는_철자_쪽을_남긴다():
    """`(A-4)/(에이 다시 사)` 는 철자/발음을 함께 적은 AI Hub 규약이다.
    정규화 없이 채점하면 STT 가 무엇을 뱉든 전부 오류가 된다."""
    assert normalize_reference("(A-4)/(에이 다시 사) 주차장까지") == "A4 주차장까지"


def test_하이픈은_공백_없이_지운다():
    """`A-4` 를 `A 4` 로 만들면 토큰이 하나 늘어 WER 분모가 부풀고,
    STT 가 `A4` 라고 붙여 쓰면 그것만으로 오류 두 개가 잡힌다."""
    assert normalize_reference("(A-4)/(에이) 확인") == "A4 확인"


def test_잡음_표시를_제거한다():
    assert normalize_reference("n/ 주차장까지 몇 키로나 남았나요?") == "주차장까지 몇 키로나 남았나요"


def test_문장부호는_양쪽에서_똑같이_지운다():
    """정답만 정리하고 가설을 안 정리하면 구두점이 전부 오류로 잡힌다."""
    assert word_error_rate("안녕하세요, 반갑습니다.", "안녕하세요 반갑습니다") == 0.0


# ── 산식 ────────────────────────────────────────────────────────────────
def test_완전히_같으면_0이다():
    assert word_error_rate("등본 발급 문의드려요", "등본 발급 문의드려요") == 0.0
    assert char_error_rate("등본 발급 문의드려요", "등본 발급 문의드려요") == 0.0


def test_한_단어_틀리면_길이분의_1이다():
    assert word_error_rate("등본 발급 문의드려요", "등본 발급 문의합니다") == 1 / 3


def test_CER_은_띄어쓰기를_보지_않는다():
    """한국어는 STT 띄어쓰기가 흔들려 WER 이 과하게 나온다 — 그래서 둘을 함께 본다."""
    assert word_error_rate("주민 등록 등본", "주민등록등본") > 0
    assert char_error_rate("주민 등록 등본", "주민등록등본") == 0.0


def test_정답이_비면_nan_이다():
    """0.0 은 「완벽하다」는 뜻이다. 잴 것이 없는 것을 만점으로 만들지 않는다(절대 원칙 2)."""
    assert math.isnan(word_error_rate("", "무언가"))
    assert math.isnan(char_error_rate("n/", "무언가"))


# ── 집계 ────────────────────────────────────────────────────────────────
def test_문장별_평균이_아니라_오류_합을_길이_합으로_나눈다():
    """짧은 발화 하나가 WER 3.0 을 찍으면 문장 평균은 그 한 건에 끌려간다."""
    pairs = [("가", "가 나 다 라"), ("가 나 다 라 마 바 사 아 자 차", "가 나 다 라 마 바 사 아 자 차")]
    # 문장 평균이면 (3.0 + 0.0)/2 = 1.5. 오류 합 / 길이 합이면 3/11.
    assert score_pairs(pairs)["wer"] == 3 / 11


def test_그룹별로_따로_낸다():
    """A-5 티켓의 완료 조건 — 「전체 평균 하나로 뭉개지 않는다」."""
    rows = [
        ("초급", "등본 발급", "등본 발급"),
        ("초급", "위임장 필요", "이 만장 피료"),
        ("고급", "등본 발급", "등본 발급"),
    ]
    result = aggregate_by_group(rows)
    assert set(result) == {"초급", "고급", "__all__"}
    assert result["고급"]["wer"] == 0.0
    assert result["초급"]["wer"] > result["고급"]["wer"]
    assert result["초급"]["n"] == 2


def test_표본_수가_함께_나간다():
    """등급별 표본이 적으면 그 수치를 믿으면 안 된다 — 판단 재료를 같이 준다."""
    assert score_pairs([("가 나", "가 나")])["n"] == 1
    assert score_pairs([])["n"] == 0
