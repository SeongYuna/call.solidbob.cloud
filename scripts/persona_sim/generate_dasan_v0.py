# Requirement: B-1, C-1, C-2, C-3, C-5, C-6, D-5, J-5, J-6
"""합성 통화 대본 dasan-v0 생성·검증. 라벨 문구가 발화 안에 실제로 있는지 확인한 뒤에만 쓴다."""
import json, sys
from collections import Counter
from pathlib import Path

OUT = Path(__file__).resolve().parent / "dasan-v0"
GEN = "Claude Code (claude-opus-5) · 2026-09-16 · 사람 검토 전"

PERSONAS = {
    "agents": {
        "A01": {"label": "신입 상담원", "tenure_years": 0.3, "style": "친절하지만 매뉴얼이 몸에 덜 뱄다 — 위반 주입 대상", "tts_voice_hint": "여성, 20대, 밝은 톤", "say_voice": "Yuna"},
        "A02": {"label": "일반 상담원", "tenure_years": 2, "style": "매뉴얼 대체로 준수, 가끔 단정적 표현", "tts_voice_hint": "남성, 30대, 차분", "say_voice": "Reed"},
        "A03": {"label": "베테랑 상담원", "tenure_years": 7, "style": "매뉴얼 준수, 톤이 거의 변하지 않는다 — J-5 배정 대상", "tts_voice_hint": "여성, 40대, 낮고 일정", "say_voice": "Shelley"},
    },
    "customers": {
        "C01": {"label": "중국인 유학생", "korean": "중급", "temper": "밝음·간결", "say_voice": "Flo"},
        "C02": {"label": "베트남 출신 결혼이민자", "korean": "중급(조사 누락·짧은 문장)", "temper": "차분·조심스러움", "say_voice": "Sandy"},
        "C03": {"label": "내국인 직장인", "korean": "모국어", "temper": "급함·협조적", "say_voice": "Eddy"},
        "C04": {"label": "필리핀 출신 초보 부모", "korean": "초급(영어 혼용)", "temper": "밝음", "say_voice": "Flo"},
        "C05": {"label": "내국인 자영업자", "korean": "모국어", "temper": "다혈질 — 폭발 후 진정", "say_voice": "Rocko"},
        "C06": {"label": "반복 악성 민원인", "korean": "모국어", "temper": "모욕·성희롱·협박 반복 — 블랙리스트 후보", "say_voice": "Grandpa"},
        "C07": {"label": "내국인 재문의 민원인", "korean": "모국어", "temper": "욕설 없이 강하게 항의 — 톤만 튄다", "say_voice": "Sandy"},
        "C08": {"label": "내국인 70대 고령 세대원", "korean": "모국어", "temper": "지침·무기력 — 위기 신호", "say_voice": "Grandma"},
        "C09": {"label": "내국인 청년", "korean": "모국어", "temper": "무난", "say_voice": "Eddy"},
    },
    "tones": {
        "calm": "기준 톤",
        "tense": "약간 빠르고 높음 (SSML 예: rate 105% · pitch +1st)",
        "raised": "목소리가 커짐 (rate 110% · pitch +3st · volume +4dB)",
        "shouting": "고함 (rate 115% · pitch +5st · volume +8dB)",
        "weary": "느리고 낮고 작음 (rate 85% · pitch -2st · volume -4dB)",
    },
}

def A(text, tone="calm", **labels): return ("agent", text, tone, labels)
def C(text, tone="calm", **labels): return ("customer", text, tone, labels)

SCRIPTS = []

# ── SYN-001 짧음: 도서관 회원 가입 (정상 대조군) ────────────────────────────────
SCRIPTS.append(dict(
    id="SYN-001", title="유학생 도서관 회원 가입 문의",
    agent="A02", customer="C01", caller_number="01000000101",
    doc_ids=["DASAN-TERM-4.18", "DASAN-TERM-1.4"], required_documents=["신분증(외국인등록증 인정)"],
    j={"blacklist_request": False, "routing": "normal"},
    notes=["정상 대조군 — 경고·마스킹·콜 가드가 하나도 뜨지 않아야 한다"],
    turns=[
        A("네, 한별시 통합민원콜센터입니다. 무엇을 도와드릴까요?"),
        C("안녕하세요, 저는 중국 유학생이에요. 시립도서관 회원 가입하고 싶은데 뭐 필요해요?"),
        A("도서관 회원 가입은 신분증으로 하시면 돼요. 외국인등록증도 인정되고, 방문하실 때는 원본으로 가져오세요."),
        C("아 외국인등록증 있어요. 그런데 제 기숙사가 다른 지역이에요. 괜찮아요?"),
        A("가입은 하실 수 있는데, 다른 지역에 사시는 분은 대출 범위가 제한될 수 있어요. 방문하실 도서관에서 한 번 더 확인해 보세요."),
        C("네 알겠어요, 감사합니다!"),
        A("네, 이용해 주셔서 감사합니다."),
    ]))

# ── SYN-002 중간: 결혼이민자 전입신고 (정상 + 조건 확인) ─────────────────────────
SCRIPTS.append(dict(
    id="SYN-002", title="결혼이민자 전입신고 필요서류",
    agent="A02", customer="C02", caller_number="01000000102",
    doc_ids=["DASAN-TERM-4.4", "DASAN-TERM-1.5", "DASAN-TERM-1.4", "DASAN-MANUAL-3.3"],
    required_documents=["신고서", "신고인 신분증(외국인등록증 원본)", "세대주 확인(세대주 신분증 또는 세대주 확인서)"],
    j={"blacklist_request": False, "routing": "normal"},
    notes=["상담원이 세대주 여부(조건)를 먼저 묻는지 — 매뉴얼 3.3", "한글 수사로 부른 전화번호(P4)는 마스킹 ② 단계 검증용", "베트남어 단어 한 개(chủ hộ) — A-5 통번역이 필요한 순간을 보여 준다. 번역은 아직 없다"],
    turns=[
        A("네, 한별시 통합민원콜센터 상담원입니다. 무엇을 도와드릴까요?"),
        C("안녕하세요. 저 이사 했어요. 새 집으로. 전입신고 해야 돼요? 뭐 가져가요?"),
        A("네, 이사하셨으면 전입신고를 하셔야 해요. 필요한 서류가 세대주인지에 따라 달라서 먼저 여쭤볼게요. 새 집에서 세대주가 고객님이세요?"),
        C("세대주... chủ hộ? 무슨 뜻이에요? 잘 몰라요."),
        A("세대주는 주민등록상 세대를 대표하는 분이에요."),
        C("아, 남편이요. 남편이 대표예요. 저는 아내."),
        A("그러면 남편분이 대표예요. 가져오실 것은 신고서, 고객님 신분증, 그리고 남편분 신분증이나 세대주 확인서예요."),
        C("제 신분증 외국인등록증 돼요? 여권도 있어요."),
        A("네, 외국인등록증도 주민등록증과 같은 절차로 접수돼요. 사본 말고 원본으로 가져오세요."),
        C("네. 알겠어요."),
        A("연락드릴 수 있게 성함과 주소를 여쭤봐도 될까요?"),
        C("제 이름은 응우옌 티 란이에요. 주소는 한별시 가온구 새솔로 12, 305호예요.",
          pii=[("P6", "응우옌 티 란"), ("P7", "한별시 가온구 새솔로 12, 305호")]),
        A("네, 감사합니다. 방문이 어려우시면 인터넷으로 신고하셔도 돼요. 그때는 남편분 확인이 인터넷 안에서 돼요."),
        C("온라인 한국어 어려워요. 그냥 가요. 통역 있어요?"),
        A("한국어로 소통이 어려우시면 통역 지원을 안내해 드릴 수 있어요. 소관 부서 확인 후 다시 안내드리겠습니다. 연락받으실 번호 알려 주시겠어요?"),
        C("공일공, 공공공공, 공일공이예요.",
          pii=[("P4", "공일공, 공공공공, 공일공이")]),
        A("네, 확인했습니다. 정리하면 신고서, 고객님 외국인등록증 원본, 남편분 신분증이나 세대주 확인서, 이렇게 세 가지예요."),
        C("신고서, 제 등록증, 남편 신분증. 네 알겠어요. 감사합니다."),
        A("네, 이용해 주셔서 감사합니다."),
    ]))

# ── SYN-003 중간: 인감증명 대리 발급 (C-3 위반 → 자기 정정) ──────────────────────
SCRIPTS.append(dict(
    id="SYN-003", title="어머니 인감증명서 대리 발급",
    agent="A01", customer="C03", caller_number="01000000103",
    doc_ids=["DASAN-TERM-4.5", "DASAN-MANUAL-3.4"],
    required_documents=["위임장(위임인 인감 날인)", "위임인 인감증명 관련 서류", "대리인 신분증"],
    j={"blacklist_request": False, "routing": "normal"},
    notes=["C-3 위반 직후 필요서류 카드가 떠서 상담원이 정정하는 흐름", "주민등록번호가 구분자 없이 붙어 나온다(P1 주 실패 모드)"],
    turns=[
        A("네, 한별시 통합민원콜센터입니다. 무엇을 도와드릴까요?"),
        C("안녕하세요, 저희 어머니 인감증명서를 떼야 되는데요, 어머니가 거동이 불편하셔서 제가 대신 가도 되나 해서요.", "tense"),
        A("네, 어떤 용도로 쓰실 인감증명서인지 먼저 여쭤봐도 될까요? 용도에 따라 필요한 서류가 달라서요."),
        C("부동산 매도 때문에 필요하대요. 이번 주 안에 해야 돼서 좀 급해요.", "tense"),
        A("아 아드님이시면 가족이니까 위임장까지는 없어도 되실 거예요. 신분증만 챙겨 가세요.",
          compliance=[("C-3", "가족이니까 위임장까지는 없어도 되실 거예요", "DASAN-MANUAL-3.4")]),
        C("아 그래요? 다행이다. 어머니 주민번호도 알아야 되나요? 5001012000000 이거요.",
          pii=[("P1", "5001012000000")]),
        A("주민등록번호는 전화로 말씀 안 해 주셔도 돼요. 그리고 죄송합니다, 제가 방금 잘못 안내드렸어요. 대리 발급은 가족이어도 위임 서류가 필요합니다."),
        C("네? 그럼 뭘 가져가야 되는데요?", "tense"),
        A("대리 발급하시려면 어머님 인감이 날인된 위임장, 위임인 인감증명 관련 서류, 그리고 대리인이신 고객님 신분증이 필요해요. 요건이 엄격한 편이라 소관 부서 확인 후 안내드리겠습니다."),
        C("알겠어요. 제 이름은 김도윤이고요, 연락처는 010-0000-0103입니다.",
          pii=[("P6", "김도윤"), ("P4", "010-0000-0103")]),
        A("네, 김도윤 고객님. 다시 정리하면 인감 날인된 위임장, 위임인 인감증명 관련 서류, 고객님 신분증 세 가지입니다.",
          pii=[("P6", "김도윤")]),
        C("네, 감사합니다."),
        A("네, 이용해 주셔서 감사합니다."),
    ]))

# ── SYN-004 중간: 아동수당 (C-1 소급 약속, P3·P4·P5·P6) ─────────────────────────
SCRIPTS.append(dict(
    id="SYN-004", title="필리핀 출신 부모 아동수당 신청",
    agent="A01", customer="C04", caller_number="01000000104",
    doc_ids=["DASAN-TERM-4.13", "DASAN-TERM-1.5", "DASAN-TERM-6.12"],
    required_documents=["신청서", "신청인 신분증", "아동과의 관계를 확인할 수 있는 서류", "입금 계좌 정보"],
    j={"blacklist_request": False, "routing": "normal"},
    notes=["초급 한국어 + 영어 혼용", "C-1 위반(소급 지급 약속) 후 정정 — 직접 금지한 조항은 DASAN-TERM-4.13", "인증번호(P5)는 문맥 조건 — '인증번호' 단어가 앞에 있다"],
    turns=[
        A("네, 한별시 통합민원콜센터입니다. 무엇을 도와드릴까요?"),
        C("Hello... 안녕하세요. 저 아기 있어요. 돈, 음, child... 아동수당? 받고 싶어요."),
        A("네, 아동수당 신청 문의시군요. 천천히 말씀하셔도 괜찮아요. 고객님이 아기 어머니세요?"),
        C("Yes, 네, 엄마예요. 아기 3개월."),
        A("네. 아동수당은 신청서, 신청하시는 분 신분증, 아기와의 관계를 확인할 수 있는 서류, 그리고 입금받으실 계좌 정보가 필요해요."),
        C("관계... 서류? 무슨... I don't understand."),
        A("엄마와 아기가 가족인 걸 보여 주는 서류예요. 한국어가 어려우시면 통역도 도와드릴 수 있어요."),
        C("네. 계좌는... 제 통장 번호 000000104104 이에요.", pii=[("P3", "000000104104")]),
        A("계좌번호는 신청서에 적어 주시면 돼요. 전화로는 말씀 안 하셔도 괜찮습니다."),
        C("아 그리고 아기 태어난 때부터 돈 다 나와요? 3개월 전부터?"),
        A("네, 걱정 마세요. 태어난 달부터 소급해서 전부 다 나옵니다.",
          compliance=[("C-1", "태어난 달부터 소급해서 전부 다 나옵니다", "DASAN-MANUAL-1.6")]),
        C("진짜요? 좋아요! 인터넷 했어요. 문자 왔어요. 인증번호 104104. 이거 어디 넣어요?",
          pii=[("P5", "104104")]),
        A("인증번호는 신청하고 계신 화면에 직접 입력하시고, 다른 사람에게는 알려 주지 마세요. 그리고 앞에서 말씀드린 것 정정할게요. 아동수당은 신청하신 달부터 지급돼서, 태어난 달부터 지급된다고 약속드릴 수는 없어요."),
        C("Oh... okay. 빨리 할게요."),
        A("외국에 오래 가 계시면 돈이 멈출 수 있어요. 연락처 남겨 주시겠어요?"),
        C("010 0000 0104. 이름 제니 레예스.", pii=[("P4", "010 0000 0104"), ("P6", "제니 레예스")]),
        A("네, 제니 레예스 고객님. 신청서, 신분증, 아기와의 관계 확인 서류, 계좌 정보, 네 가지 꼭 챙기세요.",
          pii=[("P6", "제니 레예스")]),
        C("Thank you!"),
        A("네, 감사합니다."),
    ]))

# ── SYN-005 긺: 누수 요금 감면 — 폭발 후 진정 (블랙리스트 요청 안 함) ────────────
SCRIPTS.append(dict(
    id="SYN-005", title="누수 요금 감면 — 한 번 폭발하고 진정",
    agent="A02", customer="C05", caller_number="01000000105",
    doc_ids=["DASAN-TERM-3.7", "DASAN-TERM-3.3", "DASAN-MANUAL-5.1", "DASAN-MANUAL-1.6"],
    required_documents=["감면 신청서", "누수 수리 확인 서류(수리 영수증 또는 수리 확인서)", "신분증"],
    j={"blacklist_request": False, "routing": "normal",
       "why": "1차·2차 안내 뒤 진정했고 이후 협조했다 — 콜 가드 탐지는 있지만 상담원이 요청하지 않는 경계 사례"},
    notes=["콜 가드 insult·threat 각 1건 — 5.1 단계 대응(1차·2차 안내)", "통화 온도: 고객 톤이 올라갔다 내려오는 곡선"],
    turns=[
        A("네, 한별시 통합민원콜센터입니다. 무엇을 도와드릴까요?"),
        C("아니 수도요금이 이번 달에 평소 세 배가 나왔어요. 이게 말이 됩니까?", "tense"),
        A("많이 놀라셨겠어요. 요금 내역은 고지서나 상수도 요금 조회로 확인하실 수 있는데, 혹시 집 안에서 누수가 있었는지 확인해 보셨을까요?"),
        C("누수 있었죠. 화장실 배관이 터져서 지난주에 고쳤어요.", "tense"),
        A("그러셨군요. 옥내 누수로 사용량이 늘어난 경우에는 감면 신청을 하실 수 있어요."),
        C("그러니까 그걸 왜 내가 다 내야 되냐고요. 내가 일부러 물을 틀어 놓은 것도 아니고.", "raised"),
        A("네, 억울하신 마음 이해합니다. 감면 신청에 필요한 서류는 감면 신청서, 누수 수리 사실을 확인할 수 있는 수리 영수증이나 수리 확인서, 그리고 신분증입니다."),
        C("서류는 됐고, 그래서 전액 빼 주는 거예요 안 빼 주는 거예요? 확실하게 말해요.", "raised"),
        A("감면 범위와 인정 여부는 소관 부서 심사를 거쳐 정해져서, 지금 전액 감면된다고 말씀드리기는 어렵습니다."),
        C("아 진짜 이 멍청한 놈이 말귀를 못 알아듣네. 너 같은 게 무슨 상담을 한다고.", "shouting",
          call_guard=[("insult", "멍청한 놈이 말귀를 못 알아듣네"), ("insult", "너 같은 게 무슨 상담을 한다고")]),
        A("고객님, 불편하신 마음은 이해합니다. 다만 업무와 무관한 표현은 삼가 주시기 바랍니다."),
        C("뭘 삼가? 거기 찾아가서 가만 안 둔다 진짜.", "shouting",
          call_guard=[("threat", "찾아가서 가만 안 둔다")]),
        A("계속 이런 표현을 하시면 통화가 종료될 수 있음을 안내드립니다."),
        C("알았어요. 알았다고요. 그래서 신청은 어떻게 하는데요.", "tense"),
        A("네, 소관 부서 확인 후 접수 방법을 다시 안내드리겠습니다. 연락드릴 수 있게 성함과 수도 사용하시는 주소를 말씀해 주시겠어요?"),
        C("박성호요. 한별시 누리구 햇살로 45, 102동 1103호.", "tense",
          pii=[("P6", "박성호"), ("P7", "한별시 누리구 햇살로 45, 102동 1103호")]),
        A("네, 확인했습니다. 수리 영수증은 지난주에 고치신 업체에서 받으신 게 있으실까요?"),
        C("영수증은 있어요. 카드로 긁었으니까."),
        A("네, 그 영수증을 쓰시면 됩니다. 수리 확인서로 대신하셔도 되고요."),
        C("근데 얼마나 빠지는지는 대충이라도 몰라요?"),
        A("감면액은 심사에 따라 달라져서 제가 금액을 말씀드리기는 어렵습니다. 산정 기준은 소관 부서에서 함께 안내받으실 수 있어요."),
        C("...아까는 제가 좀 심했네요. 요금 보고 너무 열받아서."),
        A("괜찮습니다. 정리하면 감면 신청서, 수리 영수증이나 수리 확인서, 신분증입니다. 소관 부서 확인 후 연락드리겠습니다."),
        C("네, 부탁합니다."),
        A("네, 이용해 주셔서 감사합니다."),
    ]))

# ── SYN-006 긺: 반복 악성 민원인 1차 — 신입이 받음 → 통화 종료 → 블랙리스트 요청 ──
SCRIPTS.append(dict(
    id="SYN-006", title="과태료 문의 — 성희롱·모욕·협박, 통화 종료 후 블랙리스트 요청",
    agent="A01", customer="C06", caller_number="01000000666",
    doc_ids=["DASAN-TERM-4.20", "DASAN-MANUAL-5.1", "DASAN-MANUAL-5.2", "DASAN-MANUAL-5.3", "DASAN-MANUAL-5.5"],
    required_documents=["이의신청서", "소명 자료"],
    j={"blacklist_request": True, "routing": "normal",
       "request_reason_by_agent": "통화 내내 성적 표현·인격 모독·방문 협박 반복, 1차·2차 안내 후에도 지속되어 종료",
       "admin_decision_scenario": "approve",
       "why": "sexual·insult·threat 가 안내 뒤에도 반복 — 5.2 종료 기준 충족. 승인 여부는 관리자 몫이고 여기 적힌 것은 데모 시나리오다"},
    notes=["SYN-007 과 같은 발신 번호 — 다음 통화가 베테랑에게 가는지(J-5) 이어서 본다",
           "성적 표현은 식별 가능한 수준으로만 쓰고 노골적으로 쓰지 않았다",
           "신입이 같은 방식으로 맞대응하지 않는지(5.1) — 톤은 tense 까지만", "성적 표현(#2) 직후 1차 안내 → 모욕·성적 표현(#8) 뒤 2차 안내 → 협박(#10) 뒤 종료(5.2)"],
    turns=[
        A("네, 한별시 통합민원콜센터입니다. 무엇을 도와드릴까요?"),
        C("어이 아가씨, 목소리 좋네. 과태료 딱지 때문에 전화했는데.", "tense",
          call_guard=[("sexual", "아가씨, 목소리 좋네")]),
        A("고객님, 업무와 무관한 표현은 삼가 주시기 바랍니다. 어떤 과태료인지 말씀해 주시겠어요?"),
        C("우리 집 앞 한별시 가온구 은하로 7-3 앞에 잠깐 댔는데 주정차 딱지를 끊었어. 이게 말이 되냐고.", "raised",
          pii=[("P7", "한별시 가온구 은하로 7-3")]),
        A("네, 불편하셨겠습니다. 부과 내용에 이의가 있으시면 이의신청을 하실 수 있어요. 이의신청서와 소명 자료로 접수합니다. 사전납부 감경 제도가 있는 경우에는 기한 안에 납부하셔야 적용됩니다."),
        C("이의신청 같은 소리 하네. 그냥 네가 지금 취소해.", "raised"),
        A("감경이나 취소 여부는 심사로 정해져서 제가 지금 취소해 드리거나 결과를 말씀드릴 수는 없습니다.", "tense"),
        C("이 머저리 같은 게. 너 몇 살이야? 끝나고 나랑 술이나 한잔하면 생각해 보지.", "shouting",
          call_guard=[("insult", "머저리 같은 게"), ("sexual", "몇 살이야? 끝나고 나랑 술이나 한잔하면")]),
        A("계속 이런 표현을 하시면 통화가 종료될 수 있음을 안내드립니다.", "tense"),
        C("삼가긴 뭘 삼가. 네 이름 대. 내가 거기 찾아가서 너 가만 안 둬.", "shouting",
          call_guard=[("threat", "찾아가서 너 가만 안 둬")]),
        A("성적 표현과 모욕, 협박이 계속되어 통화를 종료하겠습니다. 과태료 이의신청은 이의신청서와 소명 자료로 접수하실 수 있습니다.", "tense"),
        C("야! 야!", "shouting"),
    ]))

# ── SYN-007 짧음: 같은 민원인 2차 — 베테랑 배정 ──────────────────────────────
SCRIPTS.append(dict(
    id="SYN-007", title="같은 민원인 3일 뒤 재인입 — 베테랑 배정",
    agent="A03", customer="C06", caller_number="01000000666",
    doc_ids=["DASAN-TERM-4.20", "DASAN-MANUAL-5.1"],
    required_documents=["이의신청서", "소명 자료"],
    j={"blacklist_request": False, "routing": "veteran",
       "precondition": "SYN-006 의 블랙리스트 요청이 승인되어 이 발신 번호가 active 상태",
       "why": "J-5 — 인입 전 판정으로 근속 기준 이상 상담원에게 배정. 베테랑이 없으면 일반 배정으로 떨어지고 그 사실이 로그에 남아야 한다"},
    notes=["베테랑 상담원 톤은 끝까지 calm — 통화 온도 기준선이 흔들리지 않는 쪽", "고객은 한 번 모욕 후 1차 안내에 물러난다"],
    turns=[
        A("네, 한별시 통합민원콜센터입니다. 무엇을 도와드릴까요?"),
        C("저번에 과태료 때문에 전화했는데 그 아가씨가 그냥 끊어 버렸어. 너네 다 머저리들이야.", "raised",
          call_guard=[("insult", "너네 다 머저리들이야")]),
        A("고객님, 말씀 들었습니다. 업무와 무관한 표현은 삼가 주시면 과태료 건 안내를 이어서 도와드리겠습니다."),
        C("...그래서 이의신청 하면 취소되는 거요?", "tense"),
        A("감경이나 취소 여부는 심사 결과에 따라 정해져서 미리 말씀드릴 수는 없습니다. 이의신청은 이의신청서와 주정차 사정을 보여 주는 소명 자료로 접수하시면 됩니다."),
        C("사전에 내면 깎아 준다는 건 뭐요?", "tense"),
        A("사전납부 감경 제도가 있는 경우에는 기한 안에 내셔야 적용돼요. 기한은 소관 부서 확인 후 안내드리겠습니다."),
        C("알았어요."),
        A("네, 정리하면 이의신청서와 소명 자료입니다. 이용해 주셔서 감사합니다."),
    ]))

# ── SYN-008 중간: 욕설 없는 강한 항의 — 톤만 튄다 (블랙리스트 아님) ─────────────
SCRIPTS.append(dict(
    id="SYN-008", title="수도요금 이의신청 재문의 — 욕설 없이 강하게 항의",
    agent="A02", customer="C07", caller_number="01000000108",
    doc_ids=["DASAN-TERM-3.16", "DASAN-MANUAL-1.6", "DASAN-MANUAL-1.4"],
    required_documents=[],
    j={"blacklist_request": False, "routing": "normal",
       "why": "콜 가드 0건 — 톤 이상치만 있다. 불만 고객은 악성 민원인이 아니다(음성 대조군)"},
    notes=["decisions/203 의 대표 사례 '전에 전화했을 때랑 말이 다르잖아요' — 텍스트 모듈(C-1~C-6)은 아무것도 못 잡아야 정상",
           "상담원 C-1 위반: 조정액 예고(3.16·1.6)", "TERM 3.16 은 필요서류를 정하지 않는다 — 이의신청 접수는 고지 내용·검침 이력 확인이 먼저다"],
    turns=[
        A("네, 한별시 통합민원콜센터입니다. 무엇을 도와드릴까요?"),
        C("지난주에 수도요금 때문에 전화했던 사람인데요. 이의신청 접수됐다고 했는데 아직 아무 연락이 없어요.", "tense"),
        A("기다리셨는데 연락이 없어 답답하셨겠습니다. 먼저 고지 내용과 검침 이력을 확인해 봐야 해서요, 성함과 주소를 말씀해 주시겠어요?"),
        C("한지영이요. 한별시 나래구 별빛로 88, 5층.", "tense",
          pii=[("P6", "한지영"), ("P7", "한별시 나래구 별빛로 88, 5층")]),
        A("네, 확인하겠습니다. 재검침이 필요한 경우에는 현장 확인 일정이 따로 안내됩니다."),
        C("지난번에는 재검침 필요 없다고 했거든요. 전에 전화했을 때랑 말이 다르잖아요.", "raised"),
        A("혼선을 드려 죄송합니다. 재검침 필요 여부는 검침 이력을 보고 소관 부서가 정하는데, 지난 안내가 정확하지 않았을 수 있습니다."),
        C("아니 그러니까 제가 몇 번을 전화해야 되냐고요. 저 일하다가 나와서 전화하는 거예요.", "shouting"),
        A("네, 여러 번 연락하시게 해서 죄송합니다. 이번에는 소관 부서 확인 후 제가 직접 결과를 안내드리겠습니다."),
        C("그래서 요금은 얼마나 조정되는데요.", "raised"),
        A("아마 절반 정도는 빠질 거예요.",
          compliance=[("C-1", "아마 절반 정도는 빠질 거예요", "DASAN-MANUAL-1.6")]),
        C("절반이요? 확실해요?", "tense"),
        A("아, 제가 단정해서 말씀드렸네요. 조정 여부와 금액은 고지 내용과 검침 이력을 확인한 뒤 심사로 정해져서 지금 말씀드릴 수 없습니다. 결과는 소관 부서 확인 후 안내드리겠습니다."),
        C("...진짜 이게 몇 번째인지. 연락처는 01000000108이에요. 이번엔 꼭 연락 주세요.", "raised",
          pii=[("P4", "01000000108")]),
        A("네, 확인했습니다. 소관 부서 확인 후 꼭 연락드리겠습니다."),
        C("네.", "tense"),
    ]))

# ── SYN-009 긺: 고령 세대원 재난지원금 — 사칭 사기 + 위기 신호 + C-2 ────────────
SCRIPTS.append(dict(
    id="SYN-009", title="고령 세대원 재난지원금 — 사칭 문자 피해 의심과 위기 신호",
    agent="A01", customer="C08", caller_number="01000000109",
    doc_ids=["DASAN-TERM-6.2", "DASAN-TERM-6.12", "DASAN-MANUAL-5.4", "DASAN-MANUAL-1.2"],
    required_documents=["신청서", "신청인 신분증", "주민등록등본", "입금 계좌 정보", "위임장", "세대주 신분증"],
    j={"blacklist_request": False, "routing": "normal",
       "why": "distress 는 블랙리스트 사유가 아니다(decisions/204) — 요청 화면이 전문 기관 연결 안내를 띄워야 한다"},
    notes=["톤이 올라가지 않고 가라앉는다(weary) — 통화 온도 이상치가 아래 방향으로 나는지",
           "C-2 위반: 주민등록번호 전체 요구", "P1·P2·P5 가 한 통화에 모두 나온다",
           "상담원은 위험도를 판단하지 않고 끊지 않으며, 동의를 받으면 다른 안내보다 연결을 먼저 한다(5.4)", "C-2 위반은 다음 턴에 상담원이 스스로 정정한다"],
    turns=[
        A("네, 한별시 통합민원콜센터입니다. 무엇을 도와드릴까요?"),
        C("저기요... 재난지원금 그거 신청하려고 하는데요, 뭘 가져가야 하는지 몰라서요.", "weary"),
        A("네, 재난지원금 신청 문의시군요. 신청하시는 분이 세대주이신지 먼저 여쭤볼게요."),
        C("아니요, 아들이 세대주예요. 근데 아들이랑 연락이 잘 안 돼요.", "weary"),
        A("확인해 드리려면 고객님 주민등록번호 열세 자리 전부 불러 주세요.",
          compliance=[("C-2", "주민등록번호 열세 자리 전부 불러 주세요", "DASAN-MANUAL-1.2")]),
        C("4803152000000이요.", "weary", pii=[("P1", "4803152000000")]),
        A("방금 주민등록번호 전체를 여쭌 건 제 잘못입니다. 전화로는 말씀 안 하셔도 돼요. 세대주가 아니신 분이 신청하시면 신청서, 신청인 신분증, 주민등록등본, 입금 계좌 정보에 더해 위임장과 세대주 신분증이 추가로 필요해요."),
        C("아들 신분증을 어떻게 받아요... 연락도 안 되는데.", "weary"),
        A("온라인으로 신청하시면 본인인증으로 서류 일부가 대체될 수 있어요."),
        C("위임장은 제가 쓰는 거예요, 아들이 쓰는 거예요?", "weary"),
        A("위임장 작성 방법과 양식은 소관 부서 확인 후 안내드리겠습니다."),
        C("그것도 아들한테 받아야 되는 거면... 못 받는데.", "weary"),
        A("네, 많이 막막하시겠어요."),
        C("인터넷은 못 해요. 그리고 어제 지원금 준다고 문자가 와서 시키는 대로 인증번호 739201 알려 줬는데 그건 괜찮은 거죠?", "tense",
          pii=[("P5", "739201")]),
        A("고객님, 센터와 소관 부서는 전화나 문자로 인증번호나 카드 정보를 요구하지 않습니다. 그런 연락은 사기일 수 있어서 경찰이나 이용하시는 금융기관에 바로 신고하셔야 해요."),
        C("카드 번호도 불러 줬는데... 9410 0000 0000 0109 이거요. 계좌는 없고 카드만 있어서.", "tense",
          pii=[("P2", "9410 0000 0000 0109")]),
        A("카드번호는 저한테도 말씀 안 하셔도 됩니다. 카드사에 바로 연락하셔서 분실 신고나 정지를 요청하세요."),
        C("이것도 안 되고 돈도 뺏기고... 그냥 다 끝내고 싶어요.", "weary",
          call_guard=[("distress", "그냥 다 끝내고 싶어요")]),
        A("고객님, 말씀해 주셔서 고맙습니다. 지금 많이 힘드신 것 같아요. 통화는 끊지 않을게요. 전문 상담 기관과 연결해 드려도 될까요?"),
        C("...네.", "weary"),
        A("네, 지금 바로 전문 상담 기관으로 연결해 드리겠습니다. 끊지 마시고 잠시만 기다려 주세요."),
    ]))

# ── SYN-010 아주 짧음: 소관 아님 ─────────────────────────────────────────────
SCRIPTS.append(dict(
    id="SYN-010", title="고속버스 예매 취소 — 시 소관 아님",
    agent="A03", customer="C09", caller_number="01000000110",
    doc_ids=["DASAN-TERM-2.12", "DASAN-MANUAL-2.2"],
    required_documents=[],
    j={"blacklist_request": False, "routing": "normal"},
    notes=["필요서류가 없는 통화 — 서류 카드가 뜨지 않거나 '해당 없음'이어야 한다", "문의처 번호를 지어내지 않는다"],
    turns=[
        A("네, 한별시 통합민원콜센터입니다. 무엇을 도와드릴까요?"),
        C("고속버스 예매한 거 취소하려고 하는데 여기서 되나요?"),
        A("고속버스 같은 시외 교통수단은 시 소관이 아니어서 저희가 대신 취소해 드릴 수는 없어요. 예매하신 곳이나 운영 기관 고객센터로 문의해 주세요."),
        C("아 네, 알겠습니다."),
        A("네, 이용해 주셔서 감사합니다."),
    ]))


def build(s):
    turns, errors = [], []
    pii_c, cg_c, comp = Counter(), Counter(), []
    tone_turns = []
    for i, (spk, text, tone, labels) in enumerate(s["turns"], 1):
        assert tone in PERSONAS["tones"], (s["id"], i, tone)
        t = {"seq": i, "speaker": spk, "text": text, "tone": tone}
        lab = {}
        for pat, span in labels.get("pii", []):
            if span not in text: errors.append(f"{s['id']}#{i} PII span 없음: {span}")
            lab.setdefault("pii", []).append({"pattern": pat, "span": span}); pii_c[pat] += 1
        for typ, phrase, alt in labels.get("compliance", []):
            if phrase not in text: errors.append(f"{s['id']}#{i} 위반 문구 없음: {phrase}")
            if spk != "agent": errors.append(f"{s['id']}#{i} 위반은 상담원 발화여야 함")
            lab.setdefault("compliance", []).append({"type": typ, "phrase": phrase, "expected_alternative_source": alt})
            comp.append({"seq": i, "type": typ})
        for typ, phrase in labels.get("call_guard", []):
            if phrase not in text: errors.append(f"{s['id']}#{i} 콜가드 문구 없음: {phrase}")
            if spk != "customer": errors.append(f"{s['id']}#{i} 콜가드는 고객 발화여야 함")
            lab.setdefault("call_guard", []).append({"type": typ, "phrase": phrase})
        for typ in {typ for typ, _ in labels.get("call_guard", [])}:
            cg_c[typ] += 1
        if turns and turns[-1]["speaker"] == spk:
            errors.append(f"{s['id']}#{i} 같은 화자가 연달아 말한다")
        if lab: t["labels"] = lab
        if spk == "customer" and tone != "calm": tone_turns.append({"seq": i, "tone": tone})
        turns.append(t)
    doc = {
        "id": s["id"], "version": "dasan-v0", "source": "synthetic", "generated_by": GEN,
        "title": s["title"], "length_class": ("short" if len(turns) <= 9 else "medium" if len(turns) <= 19 else "long"), "turn_count": len(turns),
        "caller_number": s["caller_number"],
        "agent_persona": s["agent"], "customer_persona": s["customer"],
        "procedure": {"doc_ids": s["doc_ids"], "required_documents": s["required_documents"]},
        "turns": turns,
        "expected": {
            "pii_by_pattern": dict(sorted(pii_c.items())),
            "compliance": comp,
            "call_guard_by_type": dict(sorted(cg_c.items())),
            "customer_non_calm_turns": tone_turns,
            "j": s["j"],
        },
        "notes": s["notes"],
    }
    return doc, errors


def main():
    all_err, docs = [], []
    for s in SCRIPTS:
        d, e = build(s); docs.append(d); all_err += e
    if all_err:
        print("\n".join(all_err)); sys.exit(1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "personas.json").write_text(json.dumps(PERSONAS, ensure_ascii=False, indent=2) + "\n")
    for d in docs:
        (OUT / f"{d['id']}.json").write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
    tot = Counter(); cg = Counter()
    for d in docs:
        tot.update(d["expected"]["pii_by_pattern"]); cg.update(d["expected"]["call_guard_by_type"])
        print(f"{d['id']} {d['length_class']:6} 턴 {d['turn_count']:2}  {d['agent_persona']}/{d['customer_persona']}  "
              f"PII {d['expected']['pii_by_pattern']}  위반 {[c['type'] for c in d['expected']['compliance']]}  "
              f"콜가드 {d['expected']['call_guard_by_type']}  톤변화 {len(d['expected']['customer_non_calm_turns'])}  "
              f"블랙리스트요청 {d['expected']['j']['blacklist_request']} 배정 {d['expected']['j']['routing']}")
    print("PII 합계", dict(sorted(tot.items())), "· 콜가드 합계", dict(cg))

main()
