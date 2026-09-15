# Requirement: C-1, C-2, C-3, C-4
"""C-1~C-4 규칙. ⚠ 골든셋 문장을 그대로 넣지 않았다 — 같은 갈래의 **다른 말**로 규칙이 일반화됐는지 본다."""

from __future__ import annotations

import asyncio

import pytest

from compliance.adapter.outbound.rule_compliance_adapter import RuleComplianceAdapter
from compliance.domain.services.detector import detect


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
