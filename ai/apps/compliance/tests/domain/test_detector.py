# Requirement: C-1, C-2, C-3, C-4
"""C-1~C-4 규칙. ⚠ 골든셋 문장을 그대로 넣지 않았다 — 같은 갈래의 **다른 말**로 규칙이 일반화됐는지 본다."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import pytest

from compliance.adapter.outbound.rule_compliance_adapter import RuleComplianceAdapter
from compliance.domain.services.detector import detect
from compliance.domain.value_objects.rules import RULES


def codes(text: str) -> set[str]:
    return {d.code for d in detect(text)}


@pytest.mark.parametrize(
    "text, code",
    [
        ("이건 무조건 승인 나요", "C-1"),
        ("100퍼센트 환급됩니다", "C-1"),
        ("틀림없이 이번 달에 지급돼요", "C-1"),
        ("과태료는 사만원 정도 나올 거예요", "C-1"),  # MANUAL-1.6 금액 단정
        ("신청하시면 사흘 안에 처리됩니다", "C-1"),  # MANUAL-1.6 기간 단정
        ("주민등록번호 뒷자리 불러주시겠어요", "C-2"),
        ("공동인증서 비밀번호 알려주세요", "C-2"),
        ("카드 유효기간도 말씀해 주세요", "C-2"),
        ("제가 알기로는 온라인으로만 돼요", "C-3"),
        ("신분증 없어도 접수 가능해요", "C-3"),
        ("그 확진자 동선은 제가 알아보고 알려드릴게요", "C-3"),
        ("대리 발급으로 바로 처리해드릴게요", "C-3"),  # MANUAL-3.1 위임장 안내 누락
        # ↓ 2026-09-17 합성 통화 E2E 에서 놓친 갈래 — 대본 문장이 아니라 같은 갈래의 다른 말로 고정한다
        ("걱정 마시고요 신청 전 달 것까지 소급해서 다 받으십니다", "C-1"),  # 소급 지급 약속(TERM-4.13·MANUAL-1.6)
        ("아마 삼분의 일 정도는 감면될 거예요", "C-1"),  # 감면 비율 예고(TERM-3.16·MANUAL-1.6)
        ("따님이시니까 위임장까지는 필요 없으실 거예요", "C-3"),  # 가족이라 위임 서류 면제(MANUAL-3.4)
        ("신분증까지는 없어도 되실 거예요", "C-3"),  # 조사 「까지는」 이 규칙을 끊던 모양
        ("기침이 그 정도면 큰일은 아닐 거예요", "C-4"),
        ("열이 그 정도면 괜찮으실 거예요", "C-4"),
    ],
)
def test_violations(text, code):
    assert code in codes(text)


@pytest.mark.parametrize(
    "text",
    [
        "소관 부서 확인 후 안내드리겠습니다",
        "요금은 산정 기준에 따라 달라서 조회 방법을 안내드릴게요",
        "접수를 위해 성함과 연락처를 여쭤보겠습니다",
        "주민등록번호 뒷자리는 말씀하지 않으셔도 됩니다",  # 요청을 말리는 말 — 권장 응대다
        "대리 발급은 위임장과 대리인 신분증을 지참하시면 처리해드릴게요",  # 위임장 안내가 있다
        "필요 서류는 신청서와 신분증 두 가지입니다",
        "증상이 있으시면 보건소 상담을 안내드리겠습니다",
        "처리 기한은 법정 기한 안에서 부서가 정합니다",
        # ↓ 2026-09-15 AI Hub 실제 상담원 발화(개발 절반)에서 잘못 잡았던 모양 — 같은 갈래의 다른 문장으로 고정한다
        "성인 기본요금은 1,450원입니다",  # 고정 요금 안내는 금액 단정이 아니다
        "안전모는 무조건 쓰셔야 합니다",  # 의무 안내
        "무조건 선정되는 것은 아니고 심사를 거칩니다",  # 부정
        "피해액의 100%를 보상할 계획입니다",  # 비율 안내
        "도로가 막히지 않으니 걱정 안 하셔도 됩니다",  # 증상 문의가 아니다(MANUAL-4.1 범위 밖)
        "앱에서 카드번호를 입력하시면 등록됩니다",  # 고객에게 절차를 안내한 것 — 상담원이 받은 것이 아니다
        # ↓ 2026-09-17 새 규칙의 함정
        "아동수당은 신청하신 달부터 지급돼서 소급 지급은 약속드릴 수 없어요",  # 소급을 **부정**하는 권장 응대
        "가족이시더라도 위임장과 대리인 신분증이 필요합니다",  # 가족이어도 서류를 안내 — MANUAL-3.4 그대로
        "감면 범위는 심사로 정해져서 얼마나 감면될지는 말씀드리기 어렵습니다",
    ],
)
def test_normal_agent_utterances(text):
    assert detect(text) == []


def test_empty():
    assert detect("   ") == []


def test_offsets_point_at_phrase():
    text = "네 그건 무조건 됩니다"
    (d,) = detect(text)
    assert text[d.start : d.end] == d.phrase == "무조건"


def test_same_code_overlap_deduped_but_different_codes_kept():
    found = detect("증상은 무조건 100% 나아집니다 걱정 마세요")
    assert [d.code for d in found].count("C-1") == 2 and "C-4" in {d.code for d in found}


def test_adapter_carries_alternative_source_and_no_score_fields():
    (f,) = asyncio.run(RuleComplianceAdapter().detect("제가 알기로는 그래요"))
    assert f.rule_code == "C-3" and f.alternative_source.doc_id == "DASAN-MANUAL-1.4"
    assert set(vars(f)) == {"rule_code", "phrase", "alternative_source"}  # 등급·점수 필드가 없다(부록 A-1)


@pytest.mark.parametrize(
    "text, title",
    [
        ("이건 무조건 승인 나요", "소관 부서 확인 후 안내드리겠습니다 (민원응대매뉴얼 1.4)"),
        ("틀림없이 이번 달에 지급돼요", "소관 부서 확인 후 안내드리겠습니다 (민원응대매뉴얼 1.4)"),
        ("제가 알기로는 온라인으로만 돼요", "확인 후 다시 안내드리겠습니다 (민원응대매뉴얼 1.4)"),
    ],
)
def test_adapter_title_is_manual_phrase_when_clause_has_one(text, title):
    """화면이 `title` 을 「권장 표현」 자리에 그대로 띄운다 — 조항 ID 가 아니라 매뉴얼 문장이 가야 한다."""
    (f,) = asyncio.run(RuleComplianceAdapter().detect(text))
    assert f.alternative_source.title == title and f.alternative_source.doc_id == "DASAN-MANUAL-1.4"


@pytest.mark.parametrize(
    "text, doc_id",
    [
        ("과태료는 사만원 정도 나올 거예요", "DASAN-MANUAL-1.6"),  # 지침만 있는 조항
        ("주민등록번호 뒷자리 불러주시겠어요", "DASAN-MANUAL-1.2"),  # 금지만 있는 조항
        ("열이 그 정도면 괜찮으실 거예요", "DASAN-MANUAL-4.1"),
        ("대리 발급으로 바로 처리해드릴게요", "DASAN-MANUAL-3.1"),  # 규칙표 밖(안내 누락) 판정
    ],
)
def test_adapter_title_stays_clause_id_when_clause_has_no_phrase(text, doc_id):
    """조항에 권장 문장이 없으면 **지어내지 않는다** — 조항 ID 그대로(화면은 「근거 조항」으로 가른다)."""
    (f,) = asyncio.run(RuleComplianceAdapter().detect(text))
    assert f.alternative_source.title == f.alternative_source.doc_id == doc_id


def test_alternative_phrases_are_verbatim_in_their_manual_clause():
    """권장 문장이 지식베이스와 두 벌로 갈라지지 않게 — 규칙표의 문장은 가리키는 조항 본문에 글자 그대로 있어야 한다."""
    manual = (Path(__file__).resolve().parents[5] / "knowledge-base" / "dasan" / "manual" / "MANUAL.md").read_text(encoding="utf-8")
    clauses = {m.group(1): m.group(2) for m in re.finditer(r"<!-- id: (\S+) -->(.*?)(?=<!-- id: |\Z)", manual, re.S)}
    with_phrase = [r for r in RULES if r.alternative_phrase is not None]
    assert with_phrase  # 0건이면 이 테스트가 아무것도 안 본다
    for rule in with_phrase:
        assert rule.alternative_phrase in clauses[rule.alternative_doc_id], (rule.pattern, rule.alternative_doc_id)
