# Requirement: F-2
"""필요서류 체크리스트 규칙표 — 절차(필요서류 조항)마다 **빠짐없이 안내해야 할 서류**.

**출처는 다산 지식베이스의 필요서류 조항(`knowledge-base/dasan/terms/TERM.md` 「— 필요서류」)이다.**
이 파일은 그 조항을 코드로 옮긴 것이지 새로 만든 규칙이 아니다 — 조항이 바뀌면 문서를 먼저 고치고 여기를 맞춘다.
옮겨 적다가 어긋나지 않도록 `tests/domain/test_closure_rule_source.py` 가 **서류 이름이 조항 본문에 실제로 있는지** 대조한다.

2026-09-14 `decisions/305` 로 금융보험·쇼핑 처리유형 4종을 걷어내고 다산 절차로 바꿨다(`decisions/201` 의 F-2 전용).

## 무엇을 필수로 치는가

- **조항 본문이 조건 없이 나열한 기본 서류만** 필수다
- 조건부 추가 서류(대리 신청·대상자·추가 적립 등)는 필수로 치지 않고 `conditional` 에 적어만 둔다 —
  조건 충족 여부를 이 게이트가 모르기 때문이다. 모르는 것을 필수로 치면 해당 없는 통화마다 「누락」 경고가 뜬다
- **기본 목록 자체가 조건에 따라 갈리는 조항은 규칙을 만들지 않는다**(`EXCLUDED`). 1.3 조가 「조건을 먼저 확인한 뒤
  해당하는 목록만 안내한다」고 정한 자리다 — 조건을 판정할 규칙이 생기면 그때 넣는다.
  **단, 갈래마다 목록이 달라도 모든 갈래에 공통인 서류가 있으면 그것만 필수로 두고 나머지를 `conditional` 에 적는다**
  (2026-09-18 — 2.6·4.5·4.9·4.12 를 이렇게 옮겼다. 공통 서류는 어느 갈래에서도 빠지면 누락이므로 거짓 경고가 생기지 않는다)

순수 파이썬이다(계약 4 — domain 은 pydantic 도 모른다).
"""

from __future__ import annotations

from dataclasses import dataclass

# 1.4 조 — 신분 확인 서류로 인정하는 것. 「신분증」 을 안내했는지 볼 때 이 이름들도 같은 뜻으로 센다.
ID_KEYWORDS = ("신분증", "주민등록증", "운전면허증", "여권", "외국인등록증")
ACCOUNT_KEYWORDS = ("계좌", "통장")


@dataclass(frozen=True)
class RequiredDocument:
    """서류 하나. `name` 은 조항 본문의 표기, `keywords` 는 상담원 발화에서 안내 여부를 볼 때 찾는 말(공백 무시)."""

    name: str
    keywords: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.keywords:
            raise ValueError(f"키워드 없는 서류는 안내 여부를 볼 수 없다: {self.name}")


@dataclass(frozen=True)
class ClosureRule:
    """절차 하나의 판정 스펙. `procedure` 는 필요서류 조항 ID 다 — 추천 카드의 `source.doc_id` 와 같은 체계.

    `required` 의 **선언 순서가 곧 `missing` 의 출력 순서**다. 조항 본문의 나열 순서와 같게 둔다.
    """

    procedure: str
    title: str
    required: tuple[RequiredDocument, ...]
    conditional: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.required:
            raise ValueError(f"필수 서류가 없는 규칙은 만들지 않는다: {self.procedure}")


def _doc(name: str, *keywords: str) -> RequiredDocument:
    return RequiredDocument(name=name, keywords=keywords or (name,))


_ID = _doc("신분증", *ID_KEYWORDS)
_ACCOUNT = _doc("입금 계좌 정보", *ACCOUNT_KEYWORDS)


def _rule(procedure: str, title: str, *required: RequiredDocument, conditional: tuple[str, ...] = ()) -> ClosureRule:
    return ClosureRule(procedure=procedure, title=title, required=required, conditional=conditional)


RULES: dict[str, ClosureRule] = {
    rule.procedure: rule
    for rule in (
        _rule("DASAN-TERM-2.5", "장애인콜택시 등록 신청",
              _doc("신청서"), _ID, _doc("장애인등록증 또는 복지카드", "장애인등록증", "복지카드"),
              _doc("보행상 장애 판정을 확인할 수 있는 서류", "보행상", "장애판정"),
              conditional=("일시적 이동 불편: 진단서 또는 소견서", "대리 신청: 위임장·대리인 신분증")),
        # 2026-09-18 — 갈래(경로·장애인·국가유공자)마다 목록이 다르지만 **신분증은 어느 갈래에서도 필수**라 그것만 필수로 둔다.
        # 갈래별 추가 서류는 conditional. 합성 통화 E2E 에서 대본이 절차로 삼았는데 「절차 아님」이 나 옮겼다(장민석 님 검토)
        _rule("DASAN-TERM-2.6", "우대용 교통카드 발급",
              _ID,
              conditional=("장애인 우대용: 장애인등록증", "국가유공자 우대용: 국가유공자증", "대리 신청: 위임장·대리인 신분증")),
        _rule("DASAN-TERM-2.7", "광역알뜰교통카드 신청",
              _doc("신청서"), _ID, _doc("주소지를 확인할 수 있는 서류", "주소지"),
              conditional=("청년·저소득층 추가 적립: 연령 또는 자격 확인 서류",)),
        _rule("DASAN-TERM-2.9", "대중교통 분실물 수령",
              _ID, conditional=("대리 수령: 위임장·대리인 신분증",)),
        _rule("DASAN-TERM-3.5", "수도 사용자 명의변경",
              _doc("신청서"), _doc("신규 사용자 신분증", *ID_KEYWORDS),
              _doc("소유 또는 점유 관계를 확인할 수 있는 서류", "등기사항증명서", "등기부", "임대차계약서", "소유", "점유"),
              conditional=("대리 신청: 위임장·대리인 신분증",)),
        _rule("DASAN-TERM-3.7", "누수로 인한 요금 감면",
              _doc("감면 신청서", "신청서"), _doc("누수 수리 사실을 확인할 수 있는 서류", "수리영수증", "수리확인서", "수리"),
              _ID),
        _rule("DASAN-TERM-3.8", "세대분할 신청",
              _doc("신청서"), _ID, _doc("세대 구성을 확인할 수 있는 서류", "주민등록등본", "등본", "세대구성"),
              _doc("건축물 현황을 확인할 수 있는 서류", "건축물")),
        _rule("DASAN-TERM-3.10", "수도 신규 급수공사 신청",
              _doc("신청서"), _ID, _doc("토지·건물 소유 관계를 확인할 수 있는 서류", "등기", "소유"),
              _doc("건축 관련 인허가 서류", "인허가", "허가")),
        _rule("DASAN-TERM-3.14", "수도 폐전(사용 중지) 신청",
              _doc("신청서"), _ID, _doc("소유 또는 점유 관계를 확인할 수 있는 서류", "등기", "임대차계약서", "소유", "점유")),
        _rule("DASAN-TERM-4.3", "주민등록초본 발급",
              _ID, conditional=("대리 발급: 위임장·위임인 신분증 사본·대리인 신분증",)),
        _rule("DASAN-TERM-4.4", "전입신고",
              _doc("신고서"), _doc("신고인 신분증", *ID_KEYWORDS),
              conditional=("세대주가 아닌 사람이 신고: 세대주 확인(세대주 신분증 또는 확인서)",)),
        # 2026-09-18 — 본인 발급은 신분증 하나, 대리 발급은 위임장·인감증명 관련 서류·대리인 신분증. 신분증은 양쪽 공통
        _rule("DASAN-TERM-4.5", "인감증명·본인서명사실확인",
              _ID,
              conditional=("대리 발급: 위임장(인감 날인)·위임인 인감증명 관련 서류·대리인 신분증", "용도에 따라 추가 서류")),
        _rule("DASAN-TERM-4.6", "청소년증 발급",
              _doc("발급 신청서", "신청서"), _doc("사진"), _doc("본인 확인 서류", "본인확인", *ID_KEYWORDS),
              conditional=("보호자 대리 신청: 보호자 신분증·가족관계 확인 서류",)),
        # 2026-09-18 — 부동산(신고서·계약서·신분증)과 차량(신고서·양도증명 관련 서류·신분증)의 공통분모만 필수
        _rule("DASAN-TERM-4.9", "취득세 신고",
              _doc("신고서"), _ID,
              conditional=("부동산: 계약서", "차량: 양도증명 관련 서류", "감면 대상(생애최초 주택 구입 등): 감면 자격을 확인할 수 있는 서류")),
        _rule("DASAN-TERM-4.11", "지방세 환급 신청",
              _doc("환급 신청서", "신청서"), _ID, _doc("환급 계좌 정보", *ACCOUNT_KEYWORDS),
              conditional=("납세자와 계좌 명의자가 다름: 위임장·계좌 명의자 신분증",)),
        # 2026-09-18 — 「신청서 + 감면 사유를 확인할 수 있는 증명서」 는 사유와 무관하게 필수. 증명서의 종류만 사유별로 갈린다
        _rule("DASAN-TERM-4.12", "지방세 감면 신청",
              _doc("신청서"), _doc("감면 사유를 확인할 수 있는 증명서", "증명서", "사유"),
              conditional=("사유별 증명서 종류는 사유를 먼저 확인한 뒤 안내",)),
        _rule("DASAN-TERM-4.13", "아동수당 신청",
              _doc("신청서"), _doc("신청인 신분증", *ID_KEYWORDS),
              _doc("아동과의 관계를 확인할 수 있는 서류", "가족관계", "관계"), _ACCOUNT),
        _rule("DASAN-TERM-4.14", "다자녀 가정 지원",
              _doc("신청서"), _ID, _doc("자녀 수를 확인할 수 있는 서류", "주민등록등본", "등본", "가족관계증명서", "가족관계")),
        _rule("DASAN-TERM-4.16", "귀농·귀촌 지원사업",
              _doc("신청서"), _doc("사업계획서"), _ID, _doc("전입 사실을 확인할 수 있는 서류", "전입")),
        _rule("DASAN-TERM-4.17", "공공시설 이용·대관",
              _doc("이용 신청서", "신청서"), _doc("신청인 신분증", *ID_KEYWORDS),
              conditional=("단체 이용: 단체 확인 서류", "감면 대상: 자격 증명서")),
        _rule("DASAN-TERM-4.18", "도서관 회원 가입",
              _ID, conditional=("미성년자: 보호자 동의서·가족관계 확인 서류",)),
        _rule("DASAN-TERM-5.8", "생활지원비 신청",
              _doc("신청서"), _doc("신청인 신분증", *ID_KEYWORDS), _doc("격리 사실을 확인할 수 있는 서류", "격리"),
              _doc("가구원을 확인할 수 있는 서류", "주민등록등본", "등본", "가구원"), _ACCOUNT),
        _rule("DASAN-TERM-5.9", "유급휴가비용 지원",
              _doc("지원 신청서", "신청서"), _doc("사업자등록증"), _doc("유급휴가 부여를 확인할 수 있는 서류", "유급휴가"),
              _doc("급여 지급을 확인할 수 있는 서류", "급여"), _ACCOUNT),
        _rule("DASAN-TERM-6.2", "재난지원금 신청",
              _doc("신청서"), _doc("신청인 신분증", *ID_KEYWORDS),
              _doc("가구 구성을 확인할 수 있는 서류", "주민등록등본", "등본", "가구구성"), _ACCOUNT,
              conditional=("세대주가 아닌 사람이 신청: 위임장·세대주 신분증",)),
        _rule("DASAN-TERM-6.3", "긴급고용안정지원금 신청",
              _doc("신청서"), _ID, _doc("소득 감소를 확인할 수 있는 서류", "소득감소", "소득"),
              _doc("노무 제공 사실을 확인할 수 있는 서류", "노무"), _ACCOUNT),
        _rule("DASAN-TERM-6.4", "소상공인 지원금 신청",
              _doc("신청서"), _doc("사업자등록증"), _doc("대표자 신분증", *ID_KEYWORDS),
              _doc("매출 감소를 확인할 수 있는 서류", "매출"), _ACCOUNT),
        _rule("DASAN-TERM-6.6", "미취업 청년 지원금 신청",
              _doc("신청서"), _ID, _doc("연령을 확인할 수 있는 서류", "연령"),
              _doc("미취업 상태를 확인할 수 있는 서류", "미취업"), _ACCOUNT),
        _rule("DASAN-TERM-6.7", "아동돌봄 지원 신청",
              _doc("신청서"), _doc("신청인 신분증", *ID_KEYWORDS),
              _doc("아동과의 관계를 확인할 수 있는 서류", "가족관계", "관계"), _ACCOUNT),
        _rule("DASAN-TERM-6.9", "지원금 이의신청",
              _doc("이의신청서"), _doc("소명 자료", "소명"), _ID),
    )
}

# 필요서류를 다루지만 규칙을 만들지 않은 조항과 그 이유. 조건 판정 규칙이 생기면 여기서 빼고 RULES 에 넣는다.
EXCLUDED: dict[str, str] = {
    "DASAN-TERM-1.3": "절차가 아니라 필요서류 안내의 일반 원칙이다",
    "DASAN-TERM-1.4": "절차가 아니라 신분 확인 서류의 공통 기준이다(ID_KEYWORDS 의 출처)",
    "DASAN-TERM-3.4": "신청과 해지의 서류가 다르다",
    "DASAN-TERM-3.6": "감면 대상별로 자격 증명서가 다르다 — 대상을 먼저 확인한다",
    "DASAN-TERM-6.5": "사업주 신청분과 근로자 신청분의 서류가 다르다",
    "DASAN-TERM-6.8": "감면 대상 구분에 따라 증명서가 다르다",
}
