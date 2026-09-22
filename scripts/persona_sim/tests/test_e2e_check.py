# Requirement: A-3, C-5, C-6, F-2, SEC-1
"""`e2e/judge.py` 판정 함수 — 스택 없이 돈다. 실행: `.venv/bin/python -m pytest scripts/persona_sim/tests -q`"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from e2e.judge import (  # noqa: E402
    judge,
    judge_call_guard,
    judge_compliance,
    judge_foreign_procedures,
    judge_pii_chars,
    judge_postcall,
    judge_required_docs,
    judge_roundtrip,
    judge_sec1,
    labeled_call_guard,
    labeled_pii,
    leaked_chars,
    value_leaks,
)
from e2e.report import DISCLAIMER, to_json, to_markdown  # noqa: E402


def _script() -> dict:
    return {
        "id": "SYN-T01",
        "procedure": {"doc_ids": ["DASAN-TERM-4.13", "DASAN-MANUAL-1.6"], "required_documents": ["신청서", "신분증"]},
        "turns": [
            {"seq": 1, "speaker": "agent", "text": "네, 콜센터입니다."},
            {"seq": 2, "speaker": "customer", "text": "010 0000 0104 이고 이름은 제니 레예스.",
             "labels": {"pii": [{"pattern": "P4", "span": "010 0000 0104"}, {"pattern": "P6", "span": "제니 레예스"}]}},
            {"seq": 3, "speaker": "agent", "text": "소급해서 전부 나옵니다.",
             "labels": {"compliance": [{"type": "C-1", "phrase": "소급해서 전부 나옵니다"}]}},
            {"seq": 4, "speaker": "customer", "text": "이 머저리야.",
             "labels": {"call_guard": [{"type": "insult", "phrase": "머저리"}, {"type": "insult", "phrase": "야"}]}},
        ],
    }


def _segments(texts: dict[int, str]) -> list[dict]:
    speakers = {1: "agent", 2: "customer", 3: "agent", 4: "customer"}
    return [{"segment_id": str(i), "speaker": speakers[i], "text": t, "is_final": "true"} for i, t in texts.items()]


MASKED = {1: "네, 콜센터입니다.", 2: "[전화번호] 이고 이름은 [이름].", 3: "소급해서 전부 나옵니다.", 4: "이 머저리야."}


def test_labels_are_read_from_turns():
    assert labeled_pii(_script()) == [(2, "P4", "010 0000 0104"), (2, "P6", "제니 레예스")]
    assert labeled_call_guard(_script()) == {(4, "insult")}  # 턴 × 갈래 — 한 턴에 둘이어도 1


def test_value_leaks_sees_through_separators():
    assert value_leaks("010 0000 0104", "번호 01000000104 입니다")
    assert value_leaks("010-0000-0104", "010 0000 0104")
    assert not value_leaks("010 0000 0104", "[전화번호]")
    assert value_leaks("제니 레예스", "이름은 제니 레예스")
    assert not value_leaks("", "아무거나")


def test_roundtrip_counts_finals_and_speaker_order():
    checks = judge_roundtrip(_script(), _segments(MASKED), 4)
    assert all(c.ok for c in checks)
    short = judge_roundtrip(_script(), _segments({1: "a", 2: "b"}), 2)
    assert [c.ok for c in short] == [False, False, False]
    assert all(c.cause == "wiring" for c in short)


def test_sec1_flags_raw_pii_in_api_or_db():
    ok = judge_sec1(_script(), _segments(MASKED), MASKED)[0]
    assert ok.ok and "누출 0건" in ok.detail
    leaked_api = {**MASKED, 2: "01000000104 이고 이름은 [이름]."}
    bad = judge_sec1(_script(), _segments(leaked_api), MASKED)[0]
    assert not bad.ok and "#2 P4" in bad.detail and "API" in bad.detail and bad.cause == "rule"
    leaked_db = {**MASKED, 2: "[전화번호] 이고 이름은 제니 레예스."}
    bad_db = judge_sec1(_script(), _segments(MASKED), leaked_db)[0]
    assert not bad_db.ok and "P6" in bad_db.detail and "DB" in bad_db.detail


def test_sec1_catches_value_repeated_in_unlabeled_turn():
    repeated = {**MASKED, 3: "제니 레예스 님, 소급해서 전부 나옵니다."}
    bad = judge_sec1(_script(), _segments(repeated), repeated)[0]
    assert not bad.ok and "#3 P6" in bad.detail and "라벨은 다른 턴" in bad.detail


def test_call_guard_folds_turn_by_type_and_reports_missing_extra():
    assert judge_call_guard(_script(), [(4, "insult"), (4, "insult")])[0].ok
    missing = judge_call_guard(_script(), [])[0]
    assert not missing.ok and "누락 #4 insult" in missing.detail and missing.cause == "rule"
    extra = judge_call_guard(_script(), [(4, "insult"), (2, "threat")])[0]
    assert not extra.ok and "과잉 #2 threat" in extra.detail


def test_compliance_zero_detection_points_at_wiring():
    none = judge_compliance(_script(), [])[0]
    assert not none.ok and none.cause == "wiring"
    partial = judge_compliance(_script(), [(3, "C-2")])[0]
    assert not partial.ok and partial.cause == "rule" and "누락 #3 C-1" in partial.detail and "과잉 #3 C-2" in partial.detail
    assert judge_compliance(_script(), [(3, "C-1")])[0].ok


def _record(items: list[tuple[str, bool]], verdict: str = "complete", procedure: str = "DASAN-TERM-4.13", card_doc: str = "DASAN-TERM-4.13") -> dict:
    return {
        "closures": [{"closure_id": "1", "procedure": procedure, "verdict": "incomplete",
                      "items": [{"rank": "1", "document_name": n, "informed": "false"} for n, _ in items]},
                     {"closure_id": "2", "procedure": procedure, "verdict": verdict,
                      "items": [{"rank": str(i + 1), "document_name": n, "informed": str(ok).lower()} for i, (n, ok) in enumerate(items)]}],
        "recommendations": [{"cards": [{"source_doc_id": card_doc}]}],
        "summary_text": "요약 초안",
        "inquiry_type": "일반행정",  # D-2 — 서버는 못 가르면 「미분류」를 싣는다(decisions/323)
    }


def test_required_docs_compares_last_closure_and_cards():
    checks = judge_required_docs(_script(), _record([("신청서", True), ("신분증", True)]))
    assert [c.ok for c in checks] == [True, True, True, True, True, True]  # 끝의 하나가 「엉뚱한 절차 판정 0건」
    diff = judge_required_docs(_script(), _record([("신청서", True), ("통장 사본", True)]))
    by_name = {c.name: c for c in diff}
    assert not by_name["F-2·서류 목록 일치"].ok and "대본에만 ['신분증']" in by_name["F-2·서류 목록 일치"].detail
    assert by_name["F-2·서류 목록 일치"].cause == "script"
    incomplete = judge_required_docs(_script(), _record([("신청서", True), ("신분증", False)], verdict="incomplete"))
    assert not {c.name: c for c in incomplete}["F-2·마지막 판정 complete"].ok
    no_card = judge_required_docs(_script(), _record([("신청서", True), ("신분증", True)], card_doc="DASAN-TERM-1.1"))
    assert not {c.name: c for c in no_card}["B·필요서류 카드 노출"].ok
    absent = judge_required_docs(_script(), {"closures": [], "recommendations": []})
    assert not {c.name: c for c in absent}["F-2·절차 판정 존재"].ok


def test_required_docs_none_expects_no_closure():
    script = dict(_script(), procedure={"doc_ids": ["DASAN-TERM-9.9"], "required_documents": []})
    assert judge_required_docs(script, {"closures": [], "recommendations": []})[0].ok
    assert not judge_required_docs(script, _record([("x", True)], procedure="DASAN-TERM-9.9"))[0].ok


def test_postcall_known_gap_is_warning_not_failure():
    call = {"stt_engine": "synthetic-script", "status": "in_progress", "ended_at": None, "customer_id": "abc"}
    checks = judge_postcall({"summary_text": "초안", "inquiry_type": "일반행정"}, call)
    by_name = {c.name: c for c in checks}
    assert by_name["D-2·문의 유형 저장"].ok
    assert by_name["D-1·요약 초안 저장"].ok and by_name["통화 후·stt_engine=synthetic-script"].ok
    gap = by_name["통화 후·ended_at/status 갱신"]
    assert not gap.ok and gap.warn_only and gap.cause == "known"
    assert not judge_postcall({"summary_text": ""}, None)[0].ok


def test_postcall_inquiry_type_null_fails():
    """D-2 — `/close` 뒤 `inquiry_type` 이 NULL 이면 배선 결함이다. 못 가르면 「미분류」가 와야 한다(`w6-d2-inquiry-type-null`)."""
    by_name = {c.name: c for c in judge_postcall({"summary_text": "초안", "inquiry_type": None}, None)}
    assert not by_name["D-2·문의 유형 저장"].ok and by_name["D-2·문의 유형 저장"].cause == "wiring"
    assert {c.name: c for c in judge_postcall({"summary_text": "초안", "inquiry_type": "미분류"}, None)}["D-2·문의 유형 저장"].ok


def test_judge_verdict_ok_ignores_warnings_and_report_carries_disclaimer():
    call = {"stt_engine": "synthetic-script", "status": "in_progress", "ended_at": None, "customer_id": "abc"}
    db = {"final_texts": MASKED, "call_guard": [(4, "insult")], "compliance": [(3, "C-1")], "call": call}
    v = judge(_script(), "call-1", _segments(MASKED), _record([("신청서", True), ("신분증", True)]), db)
    assert v.ok and len(v.warned) == 1 and not v.failed
    md = to_markdown({"run_at": "t", "commit": "abc"}, [v])
    assert DISCLAIMER in md and "| SYN-T01 | `call-1` | ✅ |" in md
    js = to_json({"run_at": "t"}, [v])
    assert '"source": "synthetic"' in js and '"passed": 1' in js


def test_judge_without_db_skips_db_checks():
    v = judge(_script(), "call-2", _segments(MASKED), _record([("신청서", True), ("신분증", True)]), {})
    names = [c.name for c in v.checks]
    assert "C-6·콜 가드 라벨 재현" not in names and "왕복·DB transcript_segment 행 수" not in names
    assert "SEC-1·PII 원문 미잔존" in names


def test_required_docs_strips_parenthetical_and_falls_back_to_title_number():
    script = dict(_script(), procedure={"doc_ids": ["DASAN-TERM-4.18"], "required_documents": ["신분증(외국인등록증 인정)"]})
    record = {
        "closures": [{"closure_id": "1", "procedure": "DASAN-TERM-4.18", "verdict": "complete",
                      "items": [{"rank": "1", "document_name": "신분증", "informed": "true"}]}],
        "recommendations": [{"cards": [{"source_doc_id": None, "title": "4.18 도서관 회원 가입 — 필요서류"}]}],
    }
    by_name = {c.name: c for c in judge_required_docs(script, record)}
    assert by_name["F-2·서류 목록 일치"].ok
    assert by_name["B·필요서류 카드 노출"].ok and "제목 번호로 대조" in by_name["B·필요서류 카드 노출"].detail
    gap = by_name["B-6·카드 근거 조항 저장(source_doc_id)"]
    assert not gap.ok and gap.warn_only and gap.cause == "wiring"


# ---------------------------------------------------------------- 2026-09-22 QA 가 찾은 사각지대 둘


def test_foreign_procedure_closure_fails_even_when_script_has_no_documents():
    """SYN-010(고속버스, 서류 없음)이 운영에서 `TERM-2.9` 판정을 냈는데 ✅ 였다 — 대본 절차 밖 판정은 ❌."""
    script = dict(_script(), procedure={"doc_ids": ["DASAN-TERM-2.12", "DASAN-MANUAL-2.2"], "required_documents": []})
    record = {"closures": [{"closure_id": "1", "procedure": "DASAN-TERM-2.9", "verdict": "incomplete", "items": []},
                           {"closure_id": "2", "procedure": "DASAN-TERM-2.9", "verdict": "incomplete", "items": []}],
              "recommendations": []}
    by_name = {c.name: c for c in judge_required_docs(script, record)}
    assert by_name["F-2·필요서류 없음(판정 0건)"].ok  # 옛 검사는 그대로 — 대본 절차 안 판정만 센다
    foreign = by_name["F-2·엉뚱한 절차 판정 0건"]
    assert not foreign.ok and not foreign.warn_only and foreign.cause == "rule"
    assert "밖 판정 2건" in foreign.detail and "DASAN-TERM-2.9 incomplete·incomplete" in foreign.detail
    assert not judge(script, "c", [], record, {}).ok


def test_foreign_procedure_alongside_correct_one_is_listed_and_clean_record_passes():
    record = _record([("신청서", True), ("신분증", True)])
    record["closures"].append({"closure_id": "3", "procedure": "DASAN-TERM-3.5", "verdict": "incomplete", "items": []})
    foreign = judge_foreign_procedures(_script(), record)
    assert not foreign.ok and "밖 판정 1건" in foreign.detail and "DASAN-TERM-3.5 incomplete" in foreign.detail
    assert judge_foreign_procedures(_script(), _record([("신청서", True), ("신분증", True)])).ok
    assert judge_foreign_procedures(_script(), {"closures": []}).ok


def test_leaked_chars_catches_one_unmasked_character():
    """SYN-017#12 「다나카 유이」 → `*** *이` 가 전체 일치 검사를 통과했다 — 한 글자라도 남으면 잡는다."""
    original = "제 이름은 다나카 유이예요."
    assert leaked_chars("다나카 유이", original, "제 이름은 *** *이예요.") == "이"
    assert not value_leaks("다나카 유이", "제 이름은 *** *이예요.")  # 옛 검사는 놓친다 — 그래서 새 검사가 필요하다
    assert leaked_chars("다나카 유이", original, "제 이름은 *** **예요.") == ""
    assert leaked_chars("010-0000-0104", "번호는 010-0000-0104", "번호는 ***-****-***4") == "4"  # 구분자는 세지 않는다
    assert leaked_chars("010-0000-0104", "번호는 010-0000-0104", "번호는 ***-****-****") == ""
    # 길이가 다른 마스킹(자리 표시자)은 맞춰 본다
    assert leaked_chars("제니 레예스", "이름은 제니 레예스.", "이름은 [이름].") == ""
    assert leaked_chars("제니 레예스", "이름은 제니 레예스.", "이름은 [이름]레예스.") == "레예스"
    assert leaked_chars("없는 값", "원문", "원문") == ""


def test_pii_chars_check_fails_on_partial_leak_in_api_or_db_and_other_turns():
    script = {
        "id": "SYN-T02",
        "turns": [
            {"seq": 1, "speaker": "customer", "text": "제 이름은 다나카 유이예요.",
             "labels": {"pii": [{"pattern": "P6", "span": "다나카 유이"}]}},
            {"seq": 2, "speaker": "agent", "text": "다나카 유이 님 맞으시죠?"},
        ],
    }
    clean = {1: "제 이름은 *** **예요.", 2: "*** ** 님 맞으시죠?"}
    api = [{"segment_id": str(k), "speaker": "x", "text": v, "is_final": "true"} for k, v in clean.items()]
    assert judge_pii_chars(script, {1: clean[1], 2: clean[2]}, clean).ok
    partial_db = {**clean, 1: "제 이름은 *** *이예요."}
    bad = judge_pii_chars(script, {1: clean[1], 2: clean[2]}, partial_db)
    assert not bad.ok and bad.cause == "rule" and "#1 P6" in bad.detail and "DB 에 「이」 남음" in bad.detail
    assert "*** *이" in bad.detail
    other_turn = judge_pii_chars(script, {1: clean[1], 2: "다** ** 님 맞으시죠?"}, clean)
    assert not other_turn.ok and "#2 P6" in other_turn.detail and "라벨은 다른 턴" in other_turn.detail
    # judge() 에도 실린다 — SEC-1 은 ✅ 인데 글자 단위는 ❌
    v = judge(script, "c", [{**s, "text": partial_db[int(s["segment_id"])]} for s in api], {}, {})
    by_name = {c.name: c for c in v.checks}
    assert by_name["SEC-1·PII 원문 미잔존"].ok and not by_name["C-5·PII 글자 단위 잔존 0"].ok


def test_roundtrip_names_the_lost_last_turn():
    """운영 SYN-010 처럼 마지막 턴만 빠지면 ❌ 이고 어느 턴인지 적는다(`w6-replay-last-turn`)."""
    lost_last = judge_roundtrip(_script(), _segments({1: "a", 2: "b", 3: "c"}), 3)
    by_name = {c.name: c for c in lost_last}
    assert not by_name["왕복·API 확정 자막 수"].ok and "빠진 턴 [4]" in by_name["왕복·API 확정 자막 수"].detail
    assert not by_name["왕복·DB transcript_segment 행 수"].ok


# ---------------------------------------------------------------- 로컬 E2E 상담원 토큰


def test_agent_token_matches_server_shape_and_hash():
    """검사기가 DB 에 넣는 해시가 서버가 조회하는 해시와 같아야 한다 — 서버 모듈(표준 라이브러리뿐)을 경로로 읽어 대조한다."""
    import importlib.util

    from e2e import agent_token

    server_file = Path(__file__).resolve().parents[3] / "server" / "apps" / "agent_auth" / "domain" / "services" / "agent_token.py"
    spec = importlib.util.spec_from_file_location("server_agent_token", server_file)
    assert spec and spec.loader
    server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server)
    token = agent_token.new_token()
    assert server.looks_like_token(token)
    assert agent_token.hash_token(token) == server.hash_token(token)
    assert len(agent_token.E2E_AGENT_ID) <= 20  # agent.agent_id VARCHAR(20)


def test_agent_token_refuses_non_loopback_db_or_server():
    from e2e import agent_token

    local_db = "postgresql://callguard:callguard-dev@127.0.0.1:5432/callguard_e2e"
    assert agent_token.refusal_reason(local_db, "http://localhost:8000") == ""
    assert "운영 DB" in agent_token.refusal_reason("postgresql://u:p@db.internal:5432/callguard", "http://localhost:8000")
    assert agent_token.refusal_reason(local_db, "https://server.solidbob.cloud") != ""
    assert not agent_token.is_loopback_url("postgresql:///callguard")  # 유닉스 소켓 — 어디인지 모르니 만들지 않는다
    assert agent_token.is_loopback_url("http://[::1]:8000")
