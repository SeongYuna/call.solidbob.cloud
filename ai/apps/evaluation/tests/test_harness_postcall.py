# Requirement: D-1, D-2, E-1, E-4, QUA-1
"""하네스 `postcall` 섹션(D-1·D-2) 배선 — 미구현/표본 없음/유형 null 을 가르고, 기존 섹션을 건드리지 않는다.

가짜 포트로 배선만 본다 — 실제 포함률 수치를 여기 박지 않는다(6.2절 원칙 5). 정답 파일은 실물(`postcall-v1.json`)을 읽어
**로드가 깨지지 않는지**(대본 턴 수 드리프트 · 유형표 밖 라벨)도 함께 본다.
"""

from __future__ import annotations

import json

import pytest

from evaluation.golden_set import DEFAULT_POSTCALL_SET_PATH, PostcallGold, load_golden_set, load_postcall_set
from evaluation.harness import NO_SAMPLES, NOT_IMPLEMENTED, Ports, run_eval
from evaluation.metrics.postcall import TYPE_NULL, KeyItem
from hub.app.dtos import MaskedSpan
from hub.app.dtos.call_summary_dto import CallSummaryDraft
from hub.app.dtos.transcript_dto import TranscriptEvent
from hub.app.ports.output import MaskingPort
from hub.app.ports.output.postcall_port import PostcallPort


class _JoinAll(PostcallPort):
    """자막 전부를 이어 붙인 «요약» — 핵심 항목이 대본에 다 있으면 만점이 나와야 한다. 받은 입력도 적어 둔다."""

    def __init__(self, inquiry_type: str | None = None) -> None:
        self.inquiry_type = inquiry_type
        self.seen: list[list[TranscriptEvent]] = []

    async def summarize(self, call_id: str, segments: list[TranscriptEvent]) -> CallSummaryDraft:
        self.seen.append(segments)
        return CallSummaryDraft(call_id=call_id, summary_text=" ".join(s.text for s in segments),
                                inquiry_type=self.inquiry_type, follow_up_actions=(), confirmed=False)


class _StarDigits(MaskingPort):
    def mask(self, text: str) -> tuple[str, list[MaskedSpan]]:
        masked = "".join("*" if c.isdigit() else c for c in text)
        return masked, ([MaskedSpan(type="P4", span=(0, len(text)))] if masked != text else [])


def _gold(turns, key_items, inquiry_type="일반행정 문의") -> PostcallGold:
    return PostcallGold(id="PC-X", script_id="SYN-X", turns=turns, inquiry_type=inquiry_type, key_items=tuple(key_items))


_TURNS = [(1, "customer", "전입신고 하려는데요 01012345678"), (2, "agent", "신고서와 신분증을 가져오세요")]
_ITEMS = [KeyItem("PC-X.inq", "문의", "전입신고", ("전입신고",)), KeyItem("PC-X.doc", "서류", "신고서", ("신고서",))]


def test_포트가_없으면_미구현이다():
    assert run_eval([], Ports(), [_gold(_TURNS, _ITEMS)])["postcall"] == NOT_IMPLEMENTED


def test_포트는_있는데_정답이_없으면_NO_SAMPLES_다():
    assert run_eval([], Ports(postcall=_JoinAll()), None)["postcall"] == NO_SAMPLES
    assert run_eval([], Ports(postcall=_JoinAll()), [])["postcall"] == NO_SAMPLES


def test_유형이_null_이면_0점이_아니라_측정_불가다():
    r = run_eval([], Ports(postcall=_JoinAll(None)), [_gold(_TURNS, _ITEMS)])["postcall"]
    assert r["type_accuracy"] == TYPE_NULL
    assert r["coverage_macro"] == 1.0
    assert r["summarizer"] == "_JoinAll"


def test_유형을_내면_정확도를_숫자로_낸다():
    r = run_eval([], Ports(postcall=_JoinAll("대중교통 안내")), [_gold(_TURNS, _ITEMS)])["postcall"]
    assert r["type_accuracy"] == 0.0 and r["type_null"] == 0


def test_마스킹_포트가_있으면_운영처럼_가린_발화를_넣는다():
    port = _JoinAll()
    r = run_eval([], Ports(postcall=port, masking=_StarDigits()), [_gold(_TURNS, _ITEMS)])["postcall"]
    assert r["masked_input"] is True
    texts = [s.text for s in port.seen[0]]
    assert "01012345678" not in " ".join(texts)
    assert [s.segment_id for s in port.seen[0]] == [1, 2] and all(s.is_final for s in port.seen[0])


def test_postcall_을_꽂아도_기존_섹션_값은_그대로다():
    items = load_golden_set()
    without = run_eval(items, Ports(masking=_StarDigits()))
    with_pc = run_eval(items, Ports(masking=_StarDigits(), postcall=_JoinAll()), load_postcall_set())
    for section in without:
        if section == "postcall":
            continue
        assert repr(with_pc[section]) == repr(without[section]), section


# ── 실물 정답 파일 ────────────────────────────────────────────────────────────


def test_정답_파일은_10통화이고_대본_전체를_넣으면_핵심_항목이_전부_잡힌다():
    """허용 표기가 대본에 **글자로 없는** 항목은 어떤 발췌 요약도 맞힐 수 없다 — 라벨 오타를 여기서 잡는다."""
    cases = load_postcall_set()
    assert len(cases) == 10
    assert len({c.script_id for c in cases}) == 10
    r = run_eval([], Ports(postcall=_JoinAll()), cases)["postcall"]
    assert r["coverage_micro"] == 1.0, r["missed"]


def test_대본_턴_수가_바뀌면_로드가_멈춘다(tmp_path):
    raw = json.loads(DEFAULT_POSTCALL_SET_PATH.read_text(encoding="utf-8"))
    raw["items"][0]["turn_count"] += 1
    (tmp_path / "golden-set").mkdir()
    (tmp_path / "scripts").symlink_to(DEFAULT_POSTCALL_SET_PATH.parent.parent / "scripts")
    bad = tmp_path / "golden-set" / "postcall-v1.json"
    bad.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="턴 수"):
        load_postcall_set(bad)


def test_유형표에_없는_라벨은_로드가_멈춘다(tmp_path):
    raw = json.loads(DEFAULT_POSTCALL_SET_PATH.read_text(encoding="utf-8"))
    raw["items"][0]["inquiry_type"] = "도서관"
    (tmp_path / "golden-set").mkdir()
    (tmp_path / "scripts").symlink_to(DEFAULT_POSTCALL_SET_PATH.parent.parent / "scripts")
    bad = tmp_path / "golden-set" / "postcall-v1.json"
    bad.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="유형표"):
        load_postcall_set(bad)
