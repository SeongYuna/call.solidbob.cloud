# Requirement: A-5, COST-1
"""`measure_a5_proficiency.py` 의 순수 함수 — 표본 추출·예산 합·71479 정규화. STT 없이 돈다.
실행: `.venv/bin/python -m pytest scripts/tests -q`"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from measure_a5_proficiency import (  # noqa: E402
    LEVELS,
    Sample,
    cache_key,
    output_paths,
    project_from_credentials,
    normalize_71479,
    original_subset,
    parse_label,
    planned_seconds,
    raw_score_pairs,
    stratified_sample,
)
from evaluation.metrics.asr import normalize_reference, word_error_rate  # noqa: E402


def _pool() -> list[Sample]:
    """등급 4 × 화자 6 × 발화 5. 길이는 2~10초를 고르게 — 창(3~6초) 밖 것이 섞여 있다."""
    out = []
    for level in LEVELS:
        for spk in range(6):
            for k in range(5):
                out.append(Sample(
                    name=f"{level[:2]}{spk:02d}-{k}", user_id=f"{level[:2]}{spk:02d}", level=level,
                    language="Indonesian", task="ATQ", seconds=2.0 + 2 * k, reference="문장",
                ))
    return out


# ── 표본 추출 ────────────────────────────────────────────────────────────
def test_등급별로_정확히_per_level_건이고_길이_창을_지킨다():
    picked = stratified_sample(_pool(), per_level=8, seed=1, min_sec=3, max_sec=6)
    assert set(picked) == set(LEVELS)
    for chosen in picked.values():
        assert len(chosen) == 8
        assert all(3 <= s.seconds <= 6 for s in chosen)


def test_같은_화자는_등급당_상한까지만():
    picked = stratified_sample(_pool(), per_level=12, seed=1, min_sec=3, max_sec=6, max_per_speaker=2)
    for chosen in picked.values():
        counts: dict[str, int] = {}
        for s in chosen:
            counts[s.user_id] = counts.get(s.user_id, 0) + 1
        assert max(counts.values()) <= 2
        assert len(chosen) == 12  # 6 화자 × 2 — 창 안에 화자당 2건(4초·6초)이 있어 채워진다


def test_시드가_같으면_입력_순서가_달라도_같은_표본이다():
    pool = _pool()
    a = stratified_sample(pool, per_level=5, seed=20260921, min_sec=3, max_sec=6)
    b = stratified_sample(list(reversed(pool)), per_level=5, seed=20260921, min_sec=3, max_sec=6)
    c = stratified_sample(pool, per_level=5, seed=7, min_sec=3, max_sec=6)
    assert [s.name for s in a["Beginner"]] == [s.name for s in b["Beginner"]]
    assert [s.name for s in a["Beginner"]] != [s.name for s in c["Beginner"]]


def test_후보가_모자라면_있는_만큼만_돌려준다():
    """Fluent 처럼 적은 등급 — n 을 부풀리지 않는다(절대 원칙 2). 리포트에 n 이 그대로 나간다."""
    picked = stratified_sample(_pool(), per_level=50, seed=1, min_sec=3, max_sec=6, max_per_speaker=1)
    assert all(len(c) == 6 for c in picked.values())


# ── 예산 ────────────────────────────────────────────────────────────────
def test_원본_부분집합은_표본의_부분집합이고_예산은_두_몫의_합이다():
    picked = stratified_sample(_pool(), per_level=4, seed=1, min_sec=3, max_sec=6)
    subset = original_subset(picked, 1)
    names = {s.name for c in picked.values() for s in c}
    assert subset <= names and len(subset) == 4
    plan = planned_seconds(picked, subset)
    assert plan["narrow"] == sum(s.seconds for c in picked.values() for s in c)
    assert plan["original"] == sum(s.seconds for c in picked.values() for s in c if s.name in subset)
    assert plan["total"] == plan["narrow"] + plan["original"]


# ── 라벨 ────────────────────────────────────────────────────────────────
def test_라벨_파일명에서_화자와_과제를_읽는다():
    s = parse_label("00011-M-22-AE-A-ATQ009-0411512", {
        "UserID": "00011",
        "SpeakerMetadata": {"proficiency": "Advance", "language": "Avestan"},
        "RecordingMetadata": {"RecordedTime": 8.96, "orthographic": "저는 십오년 전에 한국어 공부를 시작했습니다."},
    })
    assert (s.user_id, s.level, s.task, s.seconds) == ("00011", "Advance", "ATQ", 8.96)


# ── 정규화 ──────────────────────────────────────────────────────────────
def test_71479_추가_규칙은_제어문자와_굽은따옴표만_건드린다():
    """전수 조사에서 나온 표기 — `\\x08`(2건) · `‘’“”`(각 1건). 나머지는 채점기 기본 규칙이 한다."""
    assert normalize_reference(normalize_71479("제 고향은\x08 카자흐스탄입니다.")) == "제 고향은 카자흐스탄입니다"
    assert normalize_reference(normalize_71479("자기 ‘남편하고’ 먹었다.")) == "자기 남편하고 먹었다"


def test_정규화_전_점수는_문장부호를_오류로_센다():
    """정규화가 점수를 얼마나 올리는지 드러내려고 전/후를 함께 낸다."""
    raw = raw_score_pairs([("안녕하세요, 반갑습니다.", "안녕하세요 반갑습니다")])
    assert raw["wer"] == 1.0  # 두 토큰 다 문장부호 때문에 불일치
    assert word_error_rate("안녕하세요, 반갑습니다.", "안녕하세요 반갑습니다") == 0.0


def test_v1_캐시_키는_그대로이고_다른_모델은_접미가_붙어_섞이지_않는다():
    # v1 캐시 100건이 해시 이름 그대로 있다 — 바꾸면 같은 오디오를 다시 사서 예산을 두 번 쓴다
    assert cache_key("abc", "v1") == "abc"
    assert cache_key("abc", "chirp_3") == "abc-chirp_3"
    assert cache_key("abc", "chirp_3") != cache_key("abc", "chirp_2")


def test_결과_파일은_모델마다_달라_v1_결과를_덮어쓰지_않는다(tmp_path):
    work, public = tmp_path / "w", tmp_path / "p"
    v1 = output_paths("v1", "2026-09-21", work, public)
    c3 = output_paths("chirp_3", "2026-09-21", work, public)
    assert v1 == (work / "2026-09-21-proficiency.json", public / "a5-wer-2026-09-21.json")
    assert c3 == (work / "2026-09-21-proficiency-chirp3.json", public / "a5-wer-2026-09-21-chirp3.json")


def test_프로젝트_ID_는_서비스_계정_JSON_에서_읽고_없으면_빈_문자열(tmp_path):
    good = tmp_path / "sa.json"
    good.write_text('{"project_id": "p-123", "client_email": "x"}', encoding="utf-8")
    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    assert project_from_credentials(str(good)) == "p-123"
    assert project_from_credentials(str(broken)) == ""
    assert project_from_credentials(str(tmp_path / "none.json")) == ""
    assert project_from_credentials(None) == ""
