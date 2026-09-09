# Requirement: 아키텍처(PostgreSQL 스키마), ERD 문서화
"""CallGuard PostgreSQL 스키마를 한 군데(TABLES)에 정의하고, 여기서
schema.sql(DDL)과 docs/erd.dot(ERD 소스)을 같이 생성한다. 스키마를 고칠 땐 이
파일만 고치고 다시 실행하면 SQL과 ERD가 항상 같은 정의를 가리키게 된다.

실행:
    .venv/bin/python db/generate_schema_docs.py

(graphviz의 `dot`이 설치돼 있으면 ERD.png까지 자동으로 렌더링하고, 지킬이 보여줄 수
있게 jekyll/assets/erd/ERD.png로도 복사한다. `brew install graphviz`로 설치.)
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

DB_DIR = Path(__file__).resolve().parent
DOCS_DIR = DB_DIR / "docs"
JEKYLL_ERD_ASSET = DB_DIR.parent / "jekyll" / "assets" / "erd" / "ERD.png"


@dataclass
class Column:
    name: str
    sql_type: str
    key: str = ""  # "PK" | "FK" | ""
    fk_ref: str | None = None  # "table.column"
    nullable: bool = True
    note: str = ""
    # 식별 관계(True) — 자식이 부모 없이는 존재 의미가 없는 약한 개체(transcript_segment,
    # masking_event 등). 비식별 관계(False, 기본값) — 부모는 참조/분류 대상일 뿐 자식은
    # 독립적 정체성을 가짐(call→customer, recommendation_card→document 등).
    # 모든 테이블이 서로게이트 PK를 쓰므로 물리적으로 부모 PK가 자식 PK에 포함되는
    # "진짜" 식별 관계는 없다 — 여기서는 개념적 강한 종속(약한 개체) 여부를 표시한다.
    identifying: bool = False
    # 서로게이트 PK 를 DB 가 채운다(AUTO_INCREMENT). 2026-08-27 추가 — 없으면 INSERT 때마다
    # "Field 'id' doesn't have a default value" 로 막힌다. 애플리케이션이 ID 를 만드는 코드는
    # 어디에도 없으므로 DB 가 채우는 것이 맞다.
    # 예외: transcript_segment.segment_id 는 게이트웨이가 정해서 보내는 계약 값이라(7.3절) 켜지 않는다.
    auto_increment: bool = False


@dataclass
class Table:
    """테이블 하나.

    2026-09-09 스키마 QA(`_project/decisions/205`)로 셋이 늘었다 —
    **복합 PK 없이는 `transcript_segment` 가 통화를 가로질러 덮어써지고**(실제로 재현했다),
    **부분 유니크 없이는 `blacklist_entry` 가 재등록을 못 받는다.**
    """

    name: str
    comment: str
    columns: list[Column] = field(default_factory=list)
    cluster: str = ""
    # 복합 PK. None 이면 `Column.key == "PK"` 하나를 쓴다(기존 동작)
    primary_key: tuple[str, ...] | None = None
    # 복합 FK: (자식 컬럼들, "부모테이블", 부모 컬럼들)
    composite_fks: list[tuple[tuple[str, ...], str, tuple[str, ...]]] = field(default_factory=list)
    unique: list[tuple[str, ...]] = field(default_factory=list)
    # (컬럼들, WHERE 절) — 「조건을 만족하는 행 안에서만」 유일. PostgreSQL 부분 인덱스다
    partial_unique: list[tuple[tuple[str, ...], str]] = field(default_factory=list)
    # 인덱스: (컬럼 표현들, WHERE 절 또는 None)
    indexes: list[tuple[tuple[str, ...], str | None]] = field(default_factory=list)


TABLES: list[Table] = [
    Table(
        "customer", "고객 — F-3(반복 문의 연결)이 참조하는 안정적 식별자. "
        "2026-08-26 도메인 4종 확정 이전엔 통신 전용 `subscriber`(+`plan`/체납·분실신고 플래그)였으나, "
        "그 필드들은 폐기된 명의변경 처리유형(TERM-5.3, 지금은 존재하지 않는 문서 ID)에만 쓰였고 "
        "4개 도메인(금융보험·다산콜센터·쇼핑·질병관리본부) 중 어디에도 대응하는 개념이 없어 제거했다 "
        "(`_project/decisions/006-db-스키마-도메인-정리.md`)",
        cluster="고객",
        columns=[
            Column("customer_id", "VARCHAR(40)", "PK", nullable=False, note="해시/난수 — 실명 저장 안 함, 도메인 공통"),
            Column("first_seen_at", "DATETIME", nullable=False),
            Column("status", "VARCHAR(20)", nullable=False),
        ],
    ),
    Table(
        "agent", "상담원 마스터 — 부록B H-4/H-5 리스크(감시 도구화)는 UI·집계 노출 문제이지 "
        "call.agent_id 존재 자체의 문제가 아니므로 최소 식별자만 둔다",
        cluster="고객",
        columns=[
            Column("agent_id", "VARCHAR(20)", "PK", nullable=False),
            Column("display_name", "VARCHAR(30)", nullable=False),
            Column("team", "VARCHAR(30)"),
            Column("role", "ENUM('agent','admin')", nullable=False,
                   note="J-4 는 관리자만 승인할 수 있는데(`decisions/204`) DB 가 그것을 "
                        "식별할 방법이 없었다 — 요청 페이로드의 문자열에만 의존했다(`decisions/205` ⑦)"),
            Column("hired_on", "DATE",
                   note="J-5 베테랑 판정(기본 3년 이상, `_project/decisions/204`). "
                        "근속 「연수」가 아니라 **입사일**을 둔다 — 연수를 저장하면 매년 "
                        "갱신해야 하고, 갱신을 잊으면 조용히 틀린 배정이 된다"),
        ],
    ),
    Table(
        "call", "통화 — D-1·D-2 결과(summary_text·inquiry_type)를 1:1이라 병합(역정규화)",
        cluster="통화",
        columns=[
            Column("call_id", "VARCHAR(40)", "PK", nullable=False),
            Column("domain", "ENUM('finance','dasan','shopping','health')", nullable=False,
                   note="4개 데모 도메인 — 검색·F-2 라우팅 기준([1.4절](/docs/01/))"),
            Column("customer_id", "VARCHAR(40)", "FK", "customer.customer_id"),
            Column("agent_id", "VARCHAR(20)", "FK", "agent.agent_id"),
            Column("started_at", "DATETIME", nullable=False),
            Column("ended_at", "DATETIME"),
            Column("channel_count", "TINYINT", nullable=False, note="V1 확인: 전부 1(모노)"),
            Column("summary_confirmed_at", "DATETIME",
                   note="D-1~D-3 — **NULL 이면 초안이다**(`decisions/205` ⑧). `CallSummaryDraft.confirmed` 를 "
                        "담을 자리가 없어서, 모델이 만든 초안과 상담원이 확정한 것을 DB 가 구분하지 "
                        "못했다 — 부록 A-1 이 금지한 「모델이 정한 것을 확정한 것처럼」이 저장 계층에서 일어난다"),
            Column("stt_engine", "VARCHAR(30)", nullable=False),
            Column("status", "VARCHAR(20)", nullable=False),
            Column("summary_text", "TEXT", note="D-1, 통화 후 생성"),
            Column("inquiry_type", "VARCHAR(30)", note="D-2, 통화 후 생성"),
        ],
    ),
    Table(
        "transcript_segment", "전사 세그먼트 — 발화 1건 = 1행 (1NF: 통화 전체를 한 칸에 몰아넣지 않음). "
        "⚠ **PK 는 `(call_id, segment_id)` 복합키다**(2026-09-09, `_project/decisions/205`) — "
        "`segment_id` 는 게이트웨이가 **통화 안에서** 매기는 순번이라(§7.3) 전역 유일하지 않다. "
        "단독 PK 로 두었을 때 두 번째 통화의 1번 발화가 첫 통화의 1번 행을 덮어쓰는 것을 실제로 재현했다",
        cluster="통화",
        primary_key=("call_id", "segment_id"),
        columns=[
            Column("segment_id", "BIGINT", nullable=False,
                   note="통화 안에서의 순번. **통화를 넘어 유일하지 않다** — call_id 와 함께 써야 한다"),
            Column("call_id", "VARCHAR(40)", "FK", "call.call_id", nullable=False, identifying=True),
            Column("speaker", "ENUM('customer','agent')", nullable=False),
            Column("text", "TEXT", nullable=False, note="마스킹 완료본만 — 원문 저장 금지 (SEC-1)"),
            Column("is_final", "BOOLEAN", nullable=False),
            Column("utterance_end_ms", "INT"),
            Column("created_at", "DATETIME", nullable=False),
        ],
    ),
    Table(
        "masking_event", "C-5 마스킹 이벤트 — 세그먼트당 여러 개 가능해 분리 (1NF)",
        cluster="통화",
        composite_fks=[(("call_id", "segment_id"), "transcript_segment", ("call_id", "segment_id"))],
        indexes=[(("\"call_id\"", "\"segment_id\""), None)],
        columns=[
            Column("id", "BIGINT", "PK", nullable=False, auto_increment=True),
            Column("call_id", "VARCHAR(40)", nullable=False,
                   note="transcript_segment 복합 FK 의 짝(`decisions/205`)"),
            Column("segment_id", "BIGINT", nullable=False, identifying=True),
            Column("pattern", "VARCHAR(4)", nullable=False, note="P1~P7"),
            Column("span_start", "INT", nullable=False),
            Column("span_end", "INT", nullable=False),
            Column("created_at", "DATETIME", nullable=False),
        ],
    ),
    Table(
        "compliance_rule", "C-1~C-4 위반 유형 카탈로그 — 팀 교차검증(팀원 ERD)에서 반영: "
        "suggestion이 C-4(권장 대체 표현 제시) 요구사항의 실제 저장 위치",
        cluster="통화",
        columns=[
            Column("rule_code", "VARCHAR(4)", "PK", nullable=False, note="C-1~C-4"),
            Column("label", "VARCHAR(50)", nullable=False),
            Column("default_severity", "ENUM('high','medium','low')", nullable=False),
            Column("suggestion", "VARCHAR(200)", note="도메인별 MANUAL 문서의 1.4절(권장 대체 표현), 예: FIN-MANUAL-1.4"),
        ],
    ),
    Table(
        "compliance_flag", "C-1~C-4 위반 탐지 — D-4(놓친 위반 표현 누적)의 원천 데이터. "
        "⚠ **C-6(고객 폭언)을 여기 담지 않는다** — `rule_code` 가 `compliance_rule`(C-1~C-4)에 FK 로 "
        "묶여 있고, 무엇보다 **화자가 반대라** 섞으면 D-4 재학습 데이터가 오염된다. C-6 은 `call_guard_flag` 다",
        cluster="통화",
        composite_fks=[(("call_id", "segment_id"), "transcript_segment", ("call_id", "segment_id"))],
        columns=[
            Column("id", "BIGINT", "PK", nullable=False, auto_increment=True),
            Column("call_id", "VARCHAR(40)", nullable=False,
                   note="transcript_segment 복합 FK 의 짝(`decisions/205`)"),
            Column("segment_id", "BIGINT", nullable=False, identifying=True),
            Column("rule_code", "VARCHAR(4)", "FK", "compliance_rule.rule_code", nullable=False),
            Column("phrase", "VARCHAR(200)", nullable=False),
            Column("confidence", "FLOAT"),
            Column("detected_at", "DATETIME", nullable=False),
        ],
    ),
    Table(
        "document", "지식베이스 문서 조항 — 실제 본문은 Elasticsearch, 여기는 참조 무결성·관리용 메타데이터. "
        "recommendation_card·closure가 참조하므로 그 앞에 정의해야 FK 생성 순서가 맞는다",
        cluster="문서",
        columns=[
            Column("document_id", "VARCHAR(30)", "PK", nullable=False, note="도메인 접두어 포함, 예: FIN-TERM-3.2"),
            Column("doc_type", "ENUM('TERM','MANUAL','POLICY')", nullable=False),
            Column("chapter", "VARCHAR(20)"),
            Column("clause", "VARCHAR(20)"),
            Column("title", "VARCHAR(100)", nullable=False),
            Column("source_path", "VARCHAR(200)", nullable=False, note="knowledge-base/ 내 경로"),
            Column("updated_at", "DATETIME", nullable=False),
        ],
    ),
    Table(
        "recommendation", "추천 트리거 이벤트 — 카드 목록은 recommendation_card로 분리 (1NF)",
        cluster="추천",
        columns=[
            Column("recommendation_id", "BIGINT", "PK", nullable=False, auto_increment=True),
            Column("call_id", "VARCHAR(40)", "FK", "call.call_id", nullable=False, identifying=True),
            Column("trigger_at_ms", "INT", nullable=False),
            Column("internal_latency_ms", "INT"),
            Column("e2e_latency_ms", "INT"),
            Column("created_at", "DATETIME", nullable=False),
        ],
    ),
    Table(
        "recommendation_card", "추천 카드 — 트리거 1건이 카드 여러 개를 낼 수 있어 분리 (1NF)",
        cluster="추천",
        columns=[
            Column("card_id", "BIGINT", "PK", nullable=False, auto_increment=True),
            Column("recommendation_id", "BIGINT", "FK", "recommendation.recommendation_id", nullable=False, identifying=True),
            Column("source_doc_id", "VARCHAR(30)", "FK", "document.document_id", note="B-6: 근거 없으면 NULL"),
            Column("title", "VARCHAR(100)", nullable=False, note="생성 모델 출력 — document.title과 다를 수 있음"),
            Column("summary", "TEXT", nullable=False),
            Column("similarity_score", "FLOAT"),
            Column("rank", "TINYINT", nullable=False),
        ],
    ),
    Table(
        "card_feedback", "카드 채택·무시 기록 (E-1) — 상담원이 추천을 실제로 썼는지. "
        "recommendation_card에 컬럼을 더하지 않고 분리한 이유: 피드백은 카드 내용과 다른 사실이고 "
        "자체 시각을 갖는다. 카드 하나에 이벤트가 여러 번 붙을 수 있어(채택→취소) 이력이 남아야 한다 — "
        "masking_event·compliance_flag와 같은 이벤트 테이블 패턴. "
        "⚠ 상담원 단위로 집계해 점수·순위를 만들지 않는다(부록 A-1) — 카드 품질을 재는 데이터다",
        cluster="추천",
        columns=[
            Column("id", "BIGINT", "PK", nullable=False, auto_increment=True),
            Column("card_id", "BIGINT", "FK", "recommendation_card.card_id", nullable=False, identifying=True),
            Column("action", "ENUM('adopted','ignored')", nullable=False),
            Column("created_at", "DATETIME", nullable=False),
        ],
    ),
    Table(
        "closure", "F-2 종결 판정 — evidence 필드를 역정규화(POLICY 문서 참고)해 하나의 넓은 표로 관리. "
        "F-2는 종결형 처리가 있는 금융보험·쇼핑에만 적용된다([1.4절](/docs/01/)) — "
        "다산콜센터·질병관리본부는 안내형 업무라 이 테이블에 행이 생기지 않는다",
        cluster="종결",
        columns=[
            Column("closure_id", "BIGINT", "PK", nullable=False, auto_increment=True, note="append-only: UPDATE 없이 INSERT만 (F-4)"),
            Column("call_id", "VARCHAR(40)", "FK", "call.call_id", nullable=False, identifying=True),
            Column("closure_type", "ENUM('상품해지','보상','반품','교환')", nullable=False,
                   note="상품해지·보상=금융보험, 반품·교환=쇼핑"),
            Column("reason", "VARCHAR(100)"),
            Column("중도해지수수료_안내", "BOOLEAN", note="상품해지 전용(금융보험) — FIN-POLICY-CLOSE-1"),
            Column("약정혜택소멸_안내", "BOOLEAN", note="상품해지 전용(금융보험) — FIN-POLICY-CLOSE-1"),
            Column("고객확인_기록", "BOOLEAN", note="상품해지 전용(금융보험) — FIN-POLICY-CLOSE-1"),
            Column("사고경위_확인", "BOOLEAN", note="보상 전용(금융보험) — FIN-POLICY-COMPENSATE-1"),
            Column("귀책여부_확인", "BOOLEAN", note="보상 전용(금융보험) — FIN-POLICY-COMPENSATE-1"),
            Column("환불금액_안내", "BOOLEAN", note="반품 전용(쇼핑) — SHOP-POLICY-RETURN-1"),
            Column("환불기간_안내", "BOOLEAN", note="반품 전용(쇼핑) — SHOP-POLICY-RETURN-1"),
            Column("상품상태_확인", "BOOLEAN", note="반품 전용(쇼핑) — SHOP-POLICY-RETURN-1"),
            Column("교환가능_확인", "BOOLEAN", note="교환 전용(쇼핑) — SHOP-POLICY-EXCHANGE-1"),
            Column("재고_확인", "BOOLEAN", note="교환 전용(쇼핑) — SHOP-POLICY-EXCHANGE-1"),
            Column("verdict", "ENUM('approved','blocked')", nullable=False),
            Column("source_doc_id", "VARCHAR(30)", "FK", "document.document_id"),
            Column("decided_at", "DATETIME", nullable=False),
        ],
    ),
    Table(
        "follow_up_action", "D-3 후속조치 항목 — 통화 1건에 여러 개 가능해 분리 (1NF)",
        cluster="후속처리",
        columns=[
            Column("id", "BIGINT", "PK", nullable=False, auto_increment=True),
            Column("call_id", "VARCHAR(40)", "FK", "call.call_id", nullable=False, identifying=True),
            Column("action_text", "VARCHAR(200)", nullable=False),
            Column("status", "VARCHAR(20)", nullable=False),
            Column("created_at", "DATETIME", nullable=False),
        ],
    ),
    Table(
        "knowledge_gap", "D-4 공백 리포트 — B/C/F 세 모듈의 실패 사례를 한 곳에 누적. "
        "⚠ `description` 은 자유 입력이라 **저장 전에 마스킹을 통과시킨다**(`decisions/205` ⑤)",
        cluster="후속처리",
        columns=[
            Column("id", "BIGINT", "PK", nullable=False, auto_increment=True),
            Column("module", "ENUM('B','C','F')", nullable=False),
            Column("description", "VARCHAR(300)", nullable=False),
            Column("call_id", "VARCHAR(40)", "FK", "call.call_id"),
            Column("call_id_seg", "VARCHAR(40)",
                   note="transcript_segment 복합 FK 의 짝. call_id 와 같은 값이지만 "
                        "이 표의 call_id 는 NULL 이 가능해 따로 둔다(`decisions/205`)"),
            Column("segment_id", "BIGINT"),
            Column("closure_id", "BIGINT", "FK", "closure.closure_id"),
            Column("created_at", "DATETIME", nullable=False),
            Column("status", "ENUM('open','resolved')", nullable=False),
        ],
    ),
    Table(
        "eval_run", "평가 실행 배치 — 6.2절 '여러 번 실행한 값 중 최저치 고정'을 위해 실행 단위로 분리",
        cluster="평가",
        columns=[
            Column("run_id", "BIGINT", "PK", nullable=False, auto_increment=True),
            Column("golden_set_version", "VARCHAR(10)", nullable=False),
            Column("git_commit", "VARCHAR(40)"),
            Column("error_rate", "FLOAT", nullable=False, note="4.2절 STT 오류 주입률 0.00~0.20, 팀 교차검증 반영"),
            Column("executed_at", "DATETIME", nullable=False),
            Column("executed_by", "VARCHAR(30)"),
        ],
    ),
    Table(
        "eval_result", "평가 결과 상세 — 실행 1건이 지표 여러 개를 내므로 분리 (1NF)",
        cluster="평가",
        columns=[
            Column("id", "BIGINT", "PK", nullable=False, auto_increment=True),
            Column("run_id", "BIGINT", "FK", "eval_run.run_id", nullable=False, identifying=True),
            Column("module", "VARCHAR(10)", nullable=False, note="B/C/C-5/F-2 등"),
            Column("metric_name", "VARCHAR(40)", nullable=False),
            Column("metric_value", "FLOAT", nullable=False),
            Column("passed_absolute_rule", "BOOLEAN", note="C-5·F-2만 해당, 그 외 NULL"),
        ],
    ),
    Table(
        "resource_center", "G-2 지역 자원 연계 — 조건부(여유 시) 모듈, 스키마만 선반영",
        cluster="G-2(조건부)",
        columns=[
            Column("center_id", "BIGINT", "PK", nullable=False, auto_increment=True),
            Column("name", "VARCHAR(100)", nullable=False),
            Column("category", "ENUM('정신건강복지센터','자살예방센터')", nullable=False),
            Column("address", "VARCHAR(200)", nullable=False),
            Column("region", "VARCHAR(30)", nullable=False),
            Column("phone", "VARCHAR(20)"),
            Column("operating_hours", "VARCHAR(50)"),
            Column("is_active", "BOOLEAN", nullable=False, note="폐지·이전 기관 반환 0건 검증용"),
        ],
    ),
    Table(
        "call_guard_flag", "C-6 고객 폭언·위기 신호 탐지 이벤트(2026-09-09, `_project/decisions/205` ②). "
        "`compliance_flag` 와 **방향이 반대다** — 저쪽은 상담원 발화, 이쪽은 고객 발화다. "
        "합치지 않는 이유 셋: ① `compliance_rule` 카탈로그가 C-1~C-4 뿐 ② 갈래 4종을 담을 컬럼이 없다 "
        "③ 화자를 섞으면 D-4 재학습 데이터가 오염된다",
        cluster="통화",
        composite_fks=[(("call_id", "segment_id"), "transcript_segment", ("call_id", "segment_id"))],
        columns=[
            Column("id", "BIGINT", "PK", nullable=False, auto_increment=True),
            Column("call_id", "VARCHAR(40)", nullable=False, identifying=True),
            Column("segment_id", "BIGINT", nullable=False),
            Column("category", "ENUM('insult','threat','sexual','distress')", nullable=False,
                   note="⚠ `distress` 는 나머지 셋과 **대응이 정반대다**(MANUAL-5.4 — 통화를 끊지 않고 "
                        "전문 기관 연결). 한 값으로 뭉치면 위기 상황에서 전화를 끊게 된다"),
            Column("phrase", "VARCHAR(200)", nullable=False,
                   note="⚠ **마스킹된 자막에서 잘라낸 구간**이다(MANUAL-5.5). 원문이 아니다"),
            Column("span_start", "INT", nullable=False, note="문자(코드포인트) 오프셋 — 7.3절"),
            Column("span_end", "INT", nullable=False),
            Column("source_doc_id", "VARCHAR(30)", "FK", "document.document_id",
                   note="근거 조항(DASAN-MANUAL-5.x). 갈래마다 다르다"),
            Column("detected_at", "DATETIME", nullable=False),
        ],
    ),
    Table(
        "voice_outlier", "D-5 통화 온도 이상 구간(2026-09-09, `_project/decisions/203`·`205` ③). "
        "⚠ **오디오를 보관하지 않으므로**(절대 원칙 7) 통화가 끝나면 재계산이 불가능하다 — "
        "저장하지 않으면 통화 후 처리가 보여줄 것이 사라진다",
        cluster="통화",
        composite_fks=[(("call_id", "segment_id"), "transcript_segment", ("call_id", "segment_id"))],
        columns=[
            Column("id", "BIGINT", "PK", nullable=False, auto_increment=True),
            Column("call_id", "VARCHAR(40)", nullable=False, identifying=True),
            Column("segment_id", "BIGINT", nullable=False),
            Column("speaker", "ENUM('customer','agent')", nullable=False,
                   note="기준선은 **화자별**로 만든다 — 절대 임계값을 쓰면 베테랑 상담사가 "
                        "통화 내내 걸린다(2026-09-09 실측)"),
            Column("robust_z", "FLOAT", nullable=False,
                   note="⚠ **화면에 내지 않는다**(부록 A-1). 저장하는 이유는 임계값 3.5 가 "
                        "「재서 고른 값이 아니라」 나중에 바꿔 재판정해야 하기 때문이다 — "
                        "저장과 표시는 다르다"),
            Column("baseline_n", "SMALLINT", nullable=False,
                   note="기준선을 만든 발화 수. 8 미만이면 애초에 판정하지 않는다"),
            Column("detected_at", "DATETIME", nullable=False),
        ],
    ),
    Table(
        "blacklist_request", "J-1·J-2 상담원이 올린 블랙리스트 전환 요청 "
        "(`_project/decisions/204`). ⚠ **시스템은 판정하지 않는다** — 상담원이 요청하고 "
        "관리자가 결정한다. 그래서 요청과 등록(blacklist_entry)이 별도 테이블이다: "
        "한 테이블에 status 만 두면 「승인된 적 없는 등록」과 「반려된 요청」이 섞인다. "
        "근거 컬럼(insult/threat/sexual/temperature)을 펼쳐 둔 것은 **역정규화**다 — "
        "요청 1건에 각 1개뿐인 값이라 별도 테이블로 빼면 조인만 늘고 얻는 것이 없다",
        cluster="J(콜 라우팅 보호)",
        columns=[
            Column("request_id", "BIGINT", "PK", nullable=False, auto_increment=True),
            Column("call_id", "VARCHAR(40)", "FK", "call.call_id", nullable=False, identifying=True),
            Column("customer_ref", "VARCHAR(64)", nullable=False,
                   note="⚠ **전화번호의 HMAC-SHA256 이다. 평문을 넣지 않는다**(`decisions/205` ③) — "
                        "전화번호는 C-5 의 P4 이고, 자막에서 지운 값을 여기 평문으로 두면 "
                        "마스킹을 앞단에 둔 의미가 사라진다. 키는 .env(SEC-2)"),
            Column("display_hint", "VARCHAR(8)",
                   note="화면 표시 전용(뒤 4자리 등). 조회·배정은 customer_ref 로만 한다"),
            Column("requested_by", "VARCHAR(20)", "FK", "agent.agent_id", nullable=False),
            Column("reason", "VARCHAR(500)", nullable=False, note="상담원이 적은 사유"),
            Column("context_excerpt", "TEXT", nullable=False,
                   note="⚠ **마스킹된 자막**이다. 원문을 넣지 않는다 — MANUAL-5.5 · C-5 · SEC-1"),
            Column("call_duration_s", "INT", nullable=False),
            Column("insult_count", "TINYINT", nullable=False),
            Column("threat_count", "TINYINT", nullable=False),
            Column("sexual_count", "TINYINT", nullable=False),
            # ⚠ distress_count 를 **일부러 두지 않는다**(`decisions/205` ④).
            # 자해·극단적 선택 암시 건수는 정신건강에 관한 정보이고, 그것이 고객 식별자와
            # 같은 행에 무기한 남으면 「이 사람이 자해를 N회 암시했다」는 레코드가 된다.
            # 화면 경고에 필요한 것은 요청 시점의 불리언 하나이고 프론트가 이미 그렇게 쓴다
            # (`hasDistress()`). MANUAL-5.4 가 위기 신호를 폭언과 **다르게** 다루라고 정한
            # 취지와도 맞는다 — 차단 대상으로 집계하지 않는다.
            Column("temperature_outliers", "TINYINT", nullable=False,
                   note="D-5 통화 온도 이상 구간 수(`decisions/203`). 점수가 아니라 건수다 — 부록 A-1"),
            Column("status", "ENUM('pending','approved','rejected')", nullable=False,
                   note="**요청의 상태만** 담는다(`decisions/205` ②). 해제(released)는 등록의 상태이지 "
                        "요청의 상태가 아니다 — 두 곳에 두면 한쪽만 갱신돼 어긋난다. "
                        "상담원은 pending 까지만 만들 수 있다"),
            Column("requested_at", "DATETIME", nullable=False),
            Column("decided_by", "VARCHAR(20)", "FK", "agent.agent_id"),
            Column("decided_at", "DATETIME"),
            Column("evidence_snapshot_at", "DATETIME", nullable=False,
                   note="위 *_count 를 집계한 시각. 원천은 call_guard_flag·voice_outlier 이고 "
                        "여기 값은 **관리자가 본 시점의 스냅샷**이다(`decisions/205`)"),
        ],
        indexes=[(('"status"', '"requested_at" DESC'), None)],
    ),
    Table(
        "blacklist_entry", "J-4 등록 **에피소드**. 고객이 아니라 「이번 등록」이 한 행이다 — "
        "해제 후 재등록되면 행이 하나 더 생기고 옛 행은 released_at 이 찍힌 채 남는다. "
        "⚠ PK 를 customer_ref 로 두었더니 **재등록이 PK 위반이거나 첫 등록 이력을 덮어썼다**"
        "(`decisions/205` ②). ⚠ **차단 목록이 아니다** — 전화는 정상적으로 받고, "
        "바뀌는 것은 누구에게 배정되는가뿐이다",
        cluster="J(콜 라우팅 보호)",
        unique=[("request_id",)],
        # 「활성 등록은 고객당 하나」만 보장한다. 이력은 쌓인다.
        # 이 인덱스가 그대로 J-5 인입 조회(released_at IS NULL)가 타는 인덱스이기도 하다.
        partial_unique=[(("customer_ref",), '"released_at" IS NULL')],
        columns=[
            Column("entry_id", "BIGINT", "PK", nullable=False, auto_increment=True),
            Column("customer_ref", "VARCHAR(64)", nullable=False,
                   note="전화번호의 HMAC. blacklist_request 와 같은 체계다(`decisions/205` ③)"),
            Column("request_id", "BIGINT", "FK", "blacklist_request.request_id",
                   nullable=False, identifying=True),
            Column("approved_at", "DATETIME", nullable=False,
                   note="등록 시작. 에피소드의 고유 사실이다. 승인자는 request.decided_by 로 따라간다"),
            Column("expires_at", "DATETIME", nullable=False,
                   note="**만료가 없으면 영구 표시가 된다**(`decisions/205` ⑤). J-5 는 "
                        "released_at IS NULL AND expires_at > now() 만 본다. 연장은 새 요청 + 새 근거로만"),
            Column("released_at", "DATETIME",
                   note="해제 시각. **행을 지우지 않는다** — 지우면 「왜 풀렸는지」가 사라진다(절대 원칙 8)"),
            Column("released_by", "VARCHAR(20)", "FK", "agent.agent_id",
                   note="⚠ 행만 남기고 이 컬럼이 없어서 **어차피 「왜 풀렸는지」가 기록되지 않았다**"),
            Column("release_reason", "VARCHAR(500)"),
            Column("note", "VARCHAR(500)",
                   note="**관리자 승인 메모**다. 요청 사유의 사본이 아니다 — 사본을 두면 "
                        "같은 개인정보가 두 벌이 된다(`decisions/205` ⑤)"),
        ],
    ),
    Table(
        "routing_log", "J-5 배정 결과. **떨어뜨린 경우를 세는 것**이 이 테이블의 목적이다 — "
        "「베테랑이 부족하다」가 fell_back 의 집계다",
        cluster="J(콜 라우팅 보호)",
        columns=[
            Column("id", "BIGINT", "PK", nullable=False, auto_increment=True),
            Column("call_id", "VARCHAR(40)", "FK", "call.call_id", nullable=False, identifying=True),
            # ⚠ customer_ref 를 **일부러 두지 않는다**(`decisions/205` ③).
            # 이 표의 목적은 fell_back 을 세는 것이고 거기에 고객 식별자가 필요 없다.
            # 두면 「특정 번호의 민원 이력」이 쌓이는데, 그건 F-3(반복 문의 연결)을
            # 폐기했던 이유를 뒷문으로 되살리는 것이다. 필요하면 call_id 로 따라간다.
            Column("is_blacklisted", "BOOLEAN", nullable=False),
            Column("assigned_agent_id", "VARCHAR(20)", "FK", "agent.agent_id"),
            Column("fell_back", "BOOLEAN", nullable=False,
                   note="베테랑이 없어 일반 배정으로 떨어진 건"),
            Column("reason", "VARCHAR(200)", nullable=False),
            Column("routed_at", "DATETIME", nullable=False),
        ],
    ),
]


def q(identifier: str) -> str:
    """식별자를 큰따옴표로 감싼다(PostgreSQL 표준). **예약어 때문에 필요하다** — 2026-08-27 확인:
    테이블 `call`, 컬럼 `rank` 가 예약어라 감싸지 않으면 CREATE TABLE 이 실패한다.
    MySQL 시절 백틱으로 하던 것과 같은 이유이고, 인용 문자만 바뀌었다
    (`_project/decisions/018-DB-PostgreSQL-전환.md`).
    예약어 목록은 버전마다 늘어나므로 개별 예외를 두지 않고 전부 감싼다."""
    return f'"{identifier}"'


def pg_type(sql_type: str, auto_increment: bool) -> tuple[str, str]:
    """MySQL 표기로 적힌 TABLES 정의를 PostgreSQL 타입으로 옮긴다.

    두 번째 반환값은 컬럼 뒤에 붙일 제약(ENUM → CHECK). PostgreSQL 에는 인라인 ENUM 이 없고,
    `CREATE TYPE` 을 쓰면 스키마 재적용 때 타입이 먼저 남아 충돌하므로 **CHECK 로 표현한다.**
    """
    t = sql_type.strip()
    if auto_increment:
        return "BIGINT GENERATED ALWAYS AS IDENTITY", ""
    if t.upper().startswith("ENUM("):
        values = t[t.index("(") + 1 : t.rindex(")")]
        return "VARCHAR(30)", f"CHECK (%s IN ({values}))"
    return {
        "TINYINT": "SMALLINT",
        "DATETIME": "TIMESTAMPTZ",
        "BOOLEAN": "BOOLEAN",
        "TEXT": "TEXT",
        "FLOAT": "REAL",
    }.get(t.upper(), t), ""


def to_sql(tables: list[Table]) -> str:
    """PostgreSQL DDL 을 만든다 (2026-08-27 MySQL 에서 전환 — decisions/018).

    MySQL 과 다른 점 셋:
      - 컬럼 주석을 인라인으로 못 단다 → 테이블 뒤에 `COMMENT ON COLUMN` 을 따로 낸다
      - `ENUM(...)` 이 없다 → `CHECK (col IN (...))` 로 표현한다 (CREATE TYPE 은 재적용 때 충돌한다)
      - `AUTO_INCREMENT` 가 없다 → `GENERATED ALWAYS AS IDENTITY`
    """
    lines = [
        "-- CallGuard PostgreSQL 스키마 — db/generate_schema_docs.py에서 자동 생성.",
        "-- 이 파일을 직접 고치지 말고 generate_schema_docs.py의 TABLES를 고친 뒤 다시 생성할 것.",
        "",
    ]
    for t in tables:
        lines.append(f"-- {t.comment}")
        lines.append(f"CREATE TABLE {q(t.name)} (")
        col_lines: list[str] = []
        fk_lines: list[str] = []
        check_lines: list[str] = []
        comment_lines: list[str] = []
        pk_col = None
        for c in t.columns:
            col_type, check_tpl = pg_type(c.sql_type, c.auto_increment)
            null_sql = "NOT NULL" if not c.nullable else "NULL"
            col_lines.append(f"    {q(c.name)} {col_type} {null_sql}")
            if check_tpl:
                check_lines.append(f"    {check_tpl % q(c.name)}")
            if c.note:
                note = c.note.replace("'", "''")
                comment_lines.append(
                    f"COMMENT ON COLUMN {q(t.name)}.{q(c.name)} IS '{note}';"
                )
            if c.key == "PK":
                pk_col = c.name
            if c.key == "FK" and c.fk_ref:
                ref_table, ref_col = c.fk_ref.split(".")
                fk_lines.append(
                    f"    FOREIGN KEY ({q(c.name)}) REFERENCES {q(ref_table)}({q(ref_col)})"
                )
        for child_cols, ref_table, ref_cols in t.composite_fks:
            child = ", ".join(q(x) for x in child_cols)
            parent = ", ".join(q(x) for x in ref_cols)
            fk_lines.append(
                f"    FOREIGN KEY ({child}) REFERENCES {q(ref_table)}({parent})"
            )
        if t.primary_key:
            col_lines.append(
                "    PRIMARY KEY (" + ", ".join(q(x) for x in t.primary_key) + ")"
            )
        elif pk_col:
            col_lines.append(f"    PRIMARY KEY ({q(pk_col)})")
        for cols in t.unique:
            col_lines.append("    UNIQUE (" + ", ".join(q(x) for x in cols) + ")")
        col_lines.extend(check_lines)
        col_lines.extend(fk_lines)
        lines.append(",\n".join(col_lines))
        lines.append(");")
        lines.extend(comment_lines)
        # 부분 유니크·인덱스는 CREATE TABLE 밖에 나온다 (PostgreSQL 문법)
        for i, (cols, where) in enumerate(t.partial_unique):
            name = f"{t.name}_uq{i}"
            cols_sql = ", ".join(q(x) for x in cols)
            lines.append(
                f"CREATE UNIQUE INDEX {q(name)} ON {q(t.name)} ({cols_sql}) WHERE {where};"
            )
        for i, (cols, where) in enumerate(t.indexes):
            name = f"{t.name}_idx{i}"
            cols_sql = ", ".join(cols)  # `col DESC` 같은 표현을 그대로 받는다
            tail = f" WHERE {where}" if where else ""
            lines.append(f"CREATE INDEX {q(name)} ON {q(t.name)} ({cols_sql}){tail};")
        lines.append("")
    return "\n".join(lines)


def to_dot(tables: list[Table]) -> str:
    clusters: dict[str, list[Table]] = {}
    for t in tables:
        clusters.setdefault(t.cluster, []).append(t)

    lines = [
        "digraph CallGuardERD {",
        '  rankdir=LR;',
        '  graph [fontname="Helvetica", nodesep=0.7, ranksep=1.3, splines=polyline];',
        '  node [fontname="Helvetica", shape=plain];',
        '  edge [fontname="Helvetica", fontsize=11, arrowtail=tee, arrowhead=crow, dir=both, color="#555555"];',
        "",
    ]

    for cluster_name, cluster_tables in clusters.items():
        lines.append(f'  subgraph "cluster_{cluster_name}" {{')
        lines.append(f'    label="{cluster_name}"; style=rounded; color="#cccccc"; fontname="Helvetica"; fontsize=13;')
        for t in cluster_tables:
            rows = [
                f'<TR><TD BGCOLOR="#2f6fed" COLSPAN="3"><FONT COLOR="white"><B>{t.name}</B></FONT></TD></TR>'
            ]
            for c in t.columns:
                key_label = ""
                if c.key == "PK":
                    key_label = "<B><U>PK</U></B>"
                elif c.key == "FK":
                    key_label = "<I>FK</I>"
                name_html = f"<B>{c.name}</B>" if c.key == "PK" else c.name
                rows.append(
                    f'<TR><TD ALIGN="LEFT">{key_label}</TD>'
                    f'<TD ALIGN="LEFT">{name_html}</TD>'
                    f'<TD ALIGN="LEFT"><FONT POINT-SIZE="10" COLOR="#666666">{c.sql_type}</FONT></TD></TR>'
                )
            label = (
                '<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4">'
                + "".join(rows)
                + "</TABLE>>"
            )
            lines.append(f'    "{t.name}" [label={label}];')
        lines.append("  }")
        lines.append("")

    for t in tables:
        for c in t.columns:
            if c.key == "FK" and c.fk_ref:
                ref_table = c.fk_ref.split(".")[0]
                # 실선 = 식별 관계(자식이 부모 없이는 존재 의미가 없는 약한 개체)
                # 점선 = 비식별 관계(부모는 참조·분류 대상일 뿐, 자식은 독립적 정체성을 가짐)
                style = "solid" if c.identifying else "dashed"
                kind_label = "식별" if c.identifying else "비식별"
                lines.append(
                    f'  "{ref_table}" -> "{t.name}" '
                    f'[label="  1:N ({c.name}, {kind_label})", style={style}];'
                )

    # 범례 — 실선/점선 구분을 다이어그램 안에서 바로 확인할 수 있게 정적 라벨 노드로 둔다
    # (레이아웃 엔진이 계산할 필요 없는 고정 텍스트라 크래시 위험이 없다).
    legend_rows = [
        '<TR><TD COLSPAN="2" BGCOLOR="#2f6fed"><FONT COLOR="white"><B>범례</B></FONT></TD></TR>',
        '<TR><TD ALIGN="LEFT">━━━━━━</TD>'
        '<TD ALIGN="LEFT">식별 관계 — 자식이 부모 없이는 존재 의미가 없는 약한 개체<BR/>'
        '(transcript_segment, masking_event, recommendation_card 등)</TD></TR>',
        '<TR><TD ALIGN="LEFT">┄┄┄┄┄┄</TD>'
        '<TD ALIGN="LEFT">비식별 관계 — 참조·분류 대상. 자식이 독립적 정체성을 가짐<BR/>'
        '(call→customer, recommendation_card→document 등)</TD></TR>',
        '<TR><TD ALIGN="LEFT">──▷</TD><TD ALIGN="LEFT">까마귀발 = N쪽(자식 여러 행)</TD></TR>',
        '<TR><TD ALIGN="LEFT">──┤</TD><TD ALIGN="LEFT">막대 = 1쪽(부모 1행)</TD></TR>',
    ]
    legend_label = (
        '<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="5">'
        + "".join(legend_rows)
        + "</TABLE>>"
    )
    lines.append(f'  "legend" [label={legend_label}, shape=plain];')

    lines.append("}")
    return "\n".join(lines)


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DB_DIR / "schema.sql").write_text(to_sql(TABLES), encoding="utf-8")
    (DOCS_DIR / "erd.dot").write_text(to_dot(TABLES), encoding="utf-8")
    print(f"생성 완료: {DB_DIR / 'schema.sql'}")
    print(f"생성 완료: {DOCS_DIR / 'erd.dot'}")
    print(f"테이블 수: {len(TABLES)}")

    if shutil.which("dot") is None:
        print("graphviz(dot)가 없어 ERD.png는 못 만들었다 — `brew install graphviz` 후 다시 실행할 것.")
        return

    erd_png = DOCS_DIR / "ERD.png"
    subprocess.run(["dot", "-Tpng", str(DOCS_DIR / "erd.dot"), "-o", str(erd_png)], check=True)
    print(f"생성 완료: {erd_png}")

    JEKYLL_ERD_ASSET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(erd_png, JEKYLL_ERD_ASSET)
    print(f"복사 완료: {JEKYLL_ERD_ASSET} (지킬 docs/16 페이지가 여기서 읽는다)")


if __name__ == "__main__":
    main()
