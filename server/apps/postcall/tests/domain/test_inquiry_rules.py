# Requirement: D-2, QUA-1
"""D-2 문의 유형 제안 — 지식베이스 장(章) 어휘로 고객 확정 발화를 가른다(`decisions/323`).

전에는 규칙표가 없어 늘 None 이었다(운영 24/24 NULL). 규칙에 안 맞으면 「미분류」 — 유형을 지어내지 않는다.
"""

import pytest

from postcall.domain.services.inquiry_rules import classify_inquiry
from postcall.domain.services.summary_rules import Utterance, build_draft


def _c(*texts):
    return [Utterance("customer", t) for t in texts]


@pytest.mark.parametrize("text, expected", [
    ("우대용 교통카드 발급하려면 뭐 가져가요", "대중교통"),
    ("누수 때문에 수도요금이 너무 많이 나왔어요", "상하수도"),
    ("주민등록초본 떼려면 뭐 필요해요", "일반행정"),
    ("코로나 확진 받았는데 생활지원비 신청하려고요", "감염병"),
    ("소상공인 지원금 신청 서류가 궁금해요", "재난·생계 지원금"),
])
def test_지식베이스_장_어휘로_가른다(text, expected):
    assert classify_inquiry(_c(text)) == expected


def test_규칙에_안_맞으면_미분류다():
    """NULL 은 「통화 후 처리 전」이다(`call_list_dto`). 처리했는데 못 가른 통화는 「미분류」로 드러낸다(`w6-d2-inquiry-type-null`)."""
    assert classify_inquiry(_c("여보세요", "네 그냥 물어볼 게 있어서요")) == "미분류"


def test_상담원_발화는_보지_않는다():
    """문의 유형은 고객이 무엇을 물었는가다 — 상담원이 다른 절차를 안내해도 바뀌지 않는다."""
    assert classify_inquiry([Utterance("agent", "지하철 정기권은 역에서"), *_c("그냥 궁금해서요")]) == "미분류"


def test_처음_문의한_발화가_정한다():
    """통화 중 곁가지(「그리고 버스는요?」)보다 처음 물은 것이 문의다."""
    assert classify_inquiry(_c("안녕하세요", "전입신고 하려는데요", "아 그리고 버스 노선도요")) == "일반행정"


def test_한_발화에_두_장이_걸리면_많이_걸린_쪽이다():
    assert classify_inquiry(_c("수도 계량기 교체랑 수질 문의인데 버스 타고 가야 해요")) == "상하수도"


def test_초안에_유형이_실린다_30자_이내():
    draft = build_draft(_c("취득세 신고 서류가 뭐예요") + [Utterance("agent", "신분증과 계약서를 준비해 주세요")])
    assert draft.inquiry_type == "일반행정"
    assert len(draft.inquiry_type) <= 30  # db call.inquiry_type VARCHAR(30)
