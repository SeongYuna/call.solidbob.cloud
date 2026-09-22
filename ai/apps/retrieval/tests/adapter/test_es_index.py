# Requirement: B-2
"""ES 색인 어댑터.

두 갈래다:
  - 아래쪽 절반은 **ES 없이** 돈다 (인덱스 이름·매핑·문서 변환). CI 가 이걸 돌린다 —
    `elasticsearch` 패키지도 설치하지 않는다.
  - `@pytest.mark.integration` 은 실제 ES 가 있을 때만 (`pytest.ini` 가 기본 제외).
    `ELASTICSEARCH_URL` 이 없으면 skip 한다.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from retrieval.adapter.outbound import es_index
from retrieval.adapter.outbound.knowledge_base_loader import load_chunks
from retrieval.domain.value_objects.chunk import DOMAINS, Chunk

KB_ROOT = Path(__file__).resolve().parents[4].parent / "knowledge-base"


def _chunk(chunk_id="FIN-TERM-1.1", domain="finance"):
    return Chunk(
        chunk_id=chunk_id,
        doc_id=chunk_id.split("#")[0],
        domain=domain,
        doc_type="TERM",
        title="목적",
        text="본문",
    )


# ─────────────────────────────────────── ES 없이 도는 것

def test_single_은_인덱스_하나다():
    assert es_index.index_names("single") == ("callguard-kb-single",)


def test_per_domain_은_도메인마다_인덱스가_하나씩이다():
    names = es_index.index_names("per-domain")
    assert len(names) == len(DOMAINS)
    assert set(names) == {f"callguard-kb-{d}" for d in DOMAINS}


@pytest.mark.parametrize("domain", DOMAINS)
def test_청크가_자기_도메인_인덱스로_간다(domain):
    c = _chunk(domain=domain)
    assert es_index.index_name_for(c, "single") == "callguard-kb-single"
    assert es_index.index_name_for(c, "per-domain") == f"callguard-kb-{domain}"


def test_모르는_레이아웃은_거부한다():
    with pytest.raises(ValueError):
        es_index.index_names("도메인별")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        es_index.index_name_for(_chunk(), "hybrid")  # type: ignore[arg-type]


def test_모르는_도메인은_거부한다():
    with pytest.raises(ValueError):
        es_index.index_name_for(_chunk(domain="telco"), "per-domain")


def test_doc_id_는_keyword_여야_한다():
    """평가 하네스가 doc_id 를 정확 일치로 대조한다. text 로 분석되면 채점이 조용히 깨진다."""
    props = es_index.build_mapping()["properties"]
    assert props["doc_id"]["type"] == "keyword"
    assert props["chunk_id"]["type"] == "keyword"
    assert props["domain"]["type"] == "keyword"


def test_본문은_nori_로_분석한다():
    props = es_index.build_mapping()["properties"]
    assert props["text"] == {"type": "text", "analyzer": "korean"}
    analysis = es_index.build_settings()["analysis"]
    assert analysis["tokenizer"]["kb_nori"]["type"] == "nori_tokenizer"
    assert analysis["analyzer"]["korean"]["tokenizer"] == "kb_nori"


def test_품사_필터를_토크나이저_바로_뒤에_기본_목록으로_둔다():
    """조사·어미가 BM25 순위를 정하던 문제(GS-205, `decisions/214`).

    순서가 뜻을 가진다 — 품사 정보는 토크나이저가 붙이므로 다른 필터보다 먼저 와야 한다.
    제외 품사는 nori 기본값이다: 사용자 정의 필터(`stoptags`)를 두지 않는다 — 골든셋에 맞춰
    목록을 고르지 않는다는 결정이 코드에 남도록 여기서 막는다.
    """
    analysis = es_index.build_settings()["analysis"]
    assert analysis["analyzer"]["korean"]["filter"] == [
        "nori_part_of_speech",
        "nori_readingform",
        "lowercase",
    ]
    assert "filter" not in analysis, "품사 필터를 사용자 정의(stoptags)로 바꾸면 decisions/214 를 먼저 고친다"


def test_사전에_없는_도메인_용어를_사용자_사전에_등록한다():
    """nori 가 명사를 용언으로 오분석하던 것들. 2026-08-27 `_analyze` 실측으로 찾았다."""
    rules = es_index.build_settings()["analysis"]["tokenizer"]["kb_nori"]["user_dictionary_rules"]
    assert "중도해지수수료 중도 해지 수수료" in rules
    assert any(r.startswith("생활하수도") for r in rules)


def test_샤드는_하나로_고정한다():
    """BM25 term statistics 는 샤드 단위다. 샤드 수가 다르면 레이아웃 비교의 교란 변수가 된다."""
    assert es_index.build_settings()["number_of_shards"] == 1


def test_두_레이아웃이_같은_매핑과_같은_문서를_쓴다():
    """비교에서 달라지는 것은 인덱스 토폴로지 하나뿐이어야 한다.

    매핑·설정은 레이아웃 인자를 받지 않으므로 정의상 같고, 문서도 같아야 한다 —
    per-domain 에서도 `domain` 필드를 빼지 않는다.
    """
    src = es_index.to_source(_chunk())
    assert src["domain"] == "finance"
    assert set(src) == {"chunk_id", "doc_id", "domain", "doc_type", "title", "text", "part"}


def test_분할된_청크는_doc_id_를_조항_ID로_유지한다():
    src = es_index.to_source(_chunk(chunk_id="FIN-TERM-1.1#1"))
    assert src["chunk_id"] == "FIN-TERM-1.1#1"
    assert src["doc_id"] == "FIN-TERM-1.1"


def test_빈_청크_목록은_거부한다():
    with pytest.raises(ValueError):
        es_index.index_chunks(object(), [], "single")


# ─────────────────────────────────────── 실제 ES 가 있을 때만

@pytest.fixture(scope="module")
def client():
    url = os.environ.get("ELASTICSEARCH_URL")
    if not url:
        pytest.skip("ELASTICSEARCH_URL 이 없다")
    es = pytest.importorskip("elasticsearch")
    c = es.Elasticsearch(url)
    if not c.ping():
        pytest.skip(f"ES 에 붙지 못했다: {url}")
    return c


@pytest.fixture(scope="module")
def chunks():
    return load_chunks(KB_ROOT)


@pytest.mark.integration
@pytest.mark.parametrize("layout", es_index.LAYOUTS)
def test_적재하면_청크_수만큼_들어간다(client, chunks, layout):
    es_index.create_indices(client, layout, recreate=True)
    counts = es_index.index_chunks(client, chunks, layout)
    assert sum(counts.values()) == len(chunks)
    if layout == "per-domain":
        for d in DOMAINS:
            expected = sum(1 for c in chunks if c.domain == d)
            assert counts[f"callguard-kb-{d}"] == expected


@pytest.mark.integration
@pytest.mark.parametrize("layout", es_index.LAYOUTS)
def test_같은_명령으로_재적재가_재현된다(client, chunks, layout):
    """w2-kb-index 의 완료 조건. `_id` 를 chunk_id 로 고정한 upsert 라 몇 번을 돌려도 같다."""
    es_index.create_indices(client, layout, recreate=True)
    first = es_index.index_chunks(client, chunks, layout)
    ids_first = _all_ids(client, layout)

    second = es_index.index_chunks(client, chunks, layout)  # recreate 없이 그대로 다시
    assert second == first
    assert _all_ids(client, layout) == ids_first


@pytest.mark.integration
@pytest.mark.parametrize(
    "term, expected_head",
    [
        ("중도해지수수료", "중도해지수수료"),
        ("생활하수도", "생활하수도"),
        ("에스컬레이션", "에스컬레이션"),
    ],
)
def test_사용자_사전이_실제로_먹는다(client, term, expected_head):
    """사전이 빠지면 "중도해지수수료" 가 `중도·해·하·아·지수·수료` 로 깨진다.

    `하`·`ᆯ` 같은 흔한 토큰이 섞이면 관계없는 문서와 매칭되고 IDF 도 오염된다.
    """
    es_index.create_indices(client, "single", recreate=True)
    resp = client.indices.analyze(
        index=es_index.SINGLE_INDEX, analyzer="korean", text=term
    )
    tokens = [t["token"] for t in resp["tokens"]]
    assert tokens[0] == expected_head, f"원형이 남지 않았다: {tokens}"
    assert not any(len(t) == 1 for t in tokens), f"1글자 오분석 토큰이 있다: {tokens}"


@pytest.mark.integration
def test_두_레이아웃의_문서_내용이_같다(client, chunks):
    """토폴로지만 다르고 문서는 같아야 비교가 공정하다."""
    for layout in es_index.LAYOUTS:
        es_index.create_indices(client, layout, recreate=True)
        es_index.index_chunks(client, chunks, layout)
    assert _all_sources(client, "single") == _all_sources(client, "per-domain")


def _all_ids(client, layout) -> set[str]:
    return set(_all_sources(client, layout))


def _all_sources(client, layout) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for name in es_index.index_names(layout):
        resp = client.search(index=name, query={"match_all": {}}, size=1000)
        for hit in resp["hits"]["hits"]:
            out[hit["_id"]] = hit["_source"]
    return out
