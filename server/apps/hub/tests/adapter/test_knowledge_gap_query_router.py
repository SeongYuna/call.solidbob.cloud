# Requirement: D-4, QUA-1
"""HTTP 표면 — 공백 리포트 조회·집계·상태 전이.

[2.5절 D-4](/docs/02/)의 누적 루프에서 **읽는 쪽**이다. 입구만 있고 읽는 경로가 없으면
신고가 쌓이기만 하고 아무도 볼 수 없다 — 루프가 닫히지 않는다.
"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from hub.app.dtos.knowledge_gap_query_dto import GapCount, KnowledgeGapRecord
from hub.app.ports.output.knowledge_gap_query_port import KnowledgeGapQueryPort
from hub.dependencies.knowledge_gap_query_provider import get_knowledge_gap_query_port
from main import app

NOW = datetime(2026, 8, 27, 9, 0, tzinfo=timezone.utc)

RECORDS = [
    KnowledgeGapRecord(gap_id=2, module="B", description="반품 배송비 부담 주체를 못 찾음",
                       status="open", created_at=NOW, call_id="c_001", segment_id=31,
                       domain="shopping"),
    KnowledgeGapRecord(gap_id=1, module="C", description="놓친 확정적 표현",
                       status="resolved", created_at=NOW),   # 통화가 없는 신고
]


class _Fake(KnowledgeGapQueryPort):
    def __init__(self, moved=True):
        self.moved = moved
        self.queries = []

    async def list_gaps(self, query):
        self.queries.append(query)
        return [r for r in RECORDS
                if (query.module is None or r.module == query.module)
                and (query.status is None or r.status == query.status)]

    async def count_gaps(self, query):
        return len(await self.list_gaps(query))

    async def count_by_module(self):
        return [GapCount("B", open=1), GapCount("C", resolved=1)]

    async def count_by_domain(self):
        return [GapCount("shopping", open=1)]

    async def update_status(self, gap_id, status):
        return self.moved


def _client(fake=None):
    app.dependency_overrides[get_knowledge_gap_query_port] = lambda: (fake or _Fake())
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_쌓인_신고를_읽을_수_있다():
    with _client() as c:
        b = c.get("/hub/knowledge-gaps").json()
    assert b["total"] == "2"
    assert [g["gap_id"] for g in b["gaps"]] == ["2", "1"]
    assert b["gaps"][0]["domain"] == "shopping"


def test_통화가_없는_신고도_사라지지_않는다():
    """`call_id` 가 NULL 인 신고를 INNER JOIN 으로 지우면 조용히 없어진다."""
    with _client() as c:
        b = c.get("/hub/knowledge-gaps").json()
    없는통화 = [g for g in b["gaps"] if g["call_id"] is None]
    assert len(없는통화) == 1 and 없는통화[0]["domain"] is None


def test_모듈과_상태로_좁힐_수_있다():
    fake = _Fake()
    with _client(fake) as c:
        c.get("/hub/knowledge-gaps", params={"module": "B", "status": "open"})
    assert fake.queries[0].module == "B" and fake.queries[0].status == "open"


def test_잘못된_모듈은_422다():
    with _client() as c:
        r = c.get("/hub/knowledge-gaps", params={"module": "Z"})
    assert r.status_code == 422


def test_limit_상한을_넘으면_422다():
    """페이지 하나로 전부 끌어오면 화면과 DB 둘 다 멈춘다."""
    with _client() as c:
        assert c.get("/hub/knowledge-gaps", params={"limit": 9999}).status_code == 422


def test_집계는_두_축으로_준다():
    with _client() as c:
        b = c.get("/hub/knowledge-gaps/summary").json()
    assert {c_["key"] for c_ in b["by_module"]} == {"B", "C"}
    assert b["total"] == "2"                    # 모듈 축 기준
    assert sum(int(c_["total"]) for c_ in b["by_domain"]) == 1   # 도메인 축은 더 작을 수 있다


def test_집계에_우선순위나_위험도가_없다():
    """부록 A-1 — 건수는 사실이고 중요도는 판단이다. 화면이 그 표현을 만들 재료를 주지 않는다."""
    with _client() as c:
        raw = c.get("/hub/knowledge-gaps/summary").text
    assert not any(w in raw for w in ("priority", "severity", "risk", "score", "위험"))


def test_보강했으면_상태를_옮긴다():
    with _client() as c:
        r = c.patch("/hub/knowledge-gaps/2", json={"status": "resolved"})
    assert r.status_code == 200 and r.json() == {"gap_id": "2", "status": "resolved"}


def test_되돌리기도_된다():
    """잘못 닫은 것을 기록에서 지우지 않고 되돌린다."""
    with _client() as c:
        assert c.patch("/hub/knowledge-gaps/2", json={"status": "open"}).status_code == 200


def test_없는_신고를_옮겼다고_하지_않는다():
    with _client(_Fake(moved=False)) as c:
        r = c.patch("/hub/knowledge-gaps/999", json={"status": "resolved"})
    assert r.status_code == 404


def test_모르는_상태로는_옮길_수_없다():
    with _client() as c:
        assert c.patch("/hub/knowledge-gaps/2", json={"status": "보류"}).status_code == 422
