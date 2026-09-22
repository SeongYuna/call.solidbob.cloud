# Requirement: B-2
"""청크 → Elasticsearch 색인. ES 클라이언트를 부르므로 adapter 계층에 둔다.

`ai/.importlinter` 의 domain-purity 계약이 `retrieval.domain → elasticsearch` 를 막는다.
청킹 규칙(순수 파이썬)은 domain 에, ES 방언은 여기에.

**지금은 `single` 로 간다** (`_project/decisions/017`). 조항이 102개뿐이라 도메인별로 나누면
인덱스당 20~34건이 되어 BM25 IDF 가 불안정해지고, 얻는 이점(도메인별 독립 재적재)은 전체
재적재가 1초도 안 걸리는 지금 있으나 마나다.

    single      callguard-kb-single                      ← 현재 쓰는 것
    per-domain  callguard-kb-{finance,dasan,shopping,health}   ← 전환 대비로 남겨둔 경로

`per-domain` 을 지우지 않은 이유: **이 결정은 지금 규모에 대한 것**이다. 도메인이 4개를 넘어
크게 늘거나(필터 선택도가 떨어져 filtered HNSW 가 무너진다), 단일 인덱스가 샤드 2개 이상을
필요로 하면(BM25 점수는 인덱스가 아니라 **샤드 단위**라 "전역 IDF" 장점이 그때 사라진다)
`--layout per-domain` 으로 전환한다. 전환 조건 전체는 `decisions/017` 참고.

**두 레이아웃의 문서와 매핑을 동일하게 유지한다** — per-domain 에도 `domain` 필드를 그대로
넣는다. 샤드 수도 1로 고정한다. 덕분에 전환이 **재적재 한 번**으로 끝나고, 나중에 양쪽을
실측 비교할 때도 인덱스 토폴로지 말고는 달라지는 것이 없다.

⚠ `callguard-kb-*` 와일드카드는 **두 레이아웃을 한꺼번에 잡는다.** 양쪽을 동시에 적재해 둔
상태라면 같은 조항이 두 번 세어진다. 인덱스 이름은 반드시 `index_names(layout)` 로 얻는다.
"""

from __future__ import annotations

from typing import Any, Literal

from retrieval.domain.value_objects.chunk import DOMAINS, Chunk

Layout = Literal["single", "per-domain"]
LAYOUTS: tuple[Layout, ...] = ("single", "per-domain")

INDEX_PREFIX = "callguard-kb"
SINGLE_INDEX = f"{INDEX_PREFIX}-single"

# 색인에 넣는 필드. Chunk 의 필드와 1:1 이다.
_SOURCE_FIELDS = ("chunk_id", "doc_id", "domain", "doc_type", "title", "text", "part")


def _check_layout(layout: str) -> None:
    if layout not in LAYOUTS:
        raise ValueError(f"모르는 레이아웃: {layout!r} (가능: {', '.join(LAYOUTS)})")


def index_names(layout: Layout, *, prefix: str = INDEX_PREFIX) -> tuple[str, ...]:
    """이 레이아웃이 쓰는 인덱스 이름 전부. 검색·삭제 모두 이걸 거쳐 얻는다.

    `prefix` 는 **통합 테스트용**이다(2026-09-22, `w6-test-hygiene-eval-wiring`). 기본값이면
    운영 이름(`callguard-kb-single`)이 그대로 나온다. 테스트가 공유 개발 인덱스를
    `recreate=True` 로 지우고 BM25 만으로 다시 채워 **dense 벡터를 조용히 0건으로 만들던** 것을
    막으려고, 테스트는 자기만의 접두어(`callguard-test-<uuid>`)를 넘긴다.
    """
    _check_layout(layout)
    if layout == "single":
        return (f"{prefix}-single",)
    return tuple(f"{prefix}-{d}" for d in DOMAINS)


def index_name_for(chunk: Chunk, layout: Layout, *, prefix: str = INDEX_PREFIX) -> str:
    """청크 하나가 들어갈 인덱스."""
    _check_layout(layout)
    if layout == "single":
        return f"{prefix}-single"
    if chunk.domain not in DOMAINS:
        raise ValueError(f"모르는 도메인: {chunk.domain!r} ({chunk.chunk_id})")
    return f"{prefix}-{chunk.domain}"


# 사전에 없어서 nori 가 **명사를 용언으로 오분석**하는 도메인 용어들.
# 형식: "표제어 조각1 조각2 …" (조각을 안 적으면 통째로 한 토큰)
#
# 2026-08-27 실측으로 찾았다 — 조항 제목의 4글자 이상 명사 24개를 `_analyze` 에 넣어
# 용언 활용 토큰(하·되·았·ᆫ·ᄆ …)이 섞이는 것만 골랐다.
#
#   중도해지수수료  → 중도 · 해 · 하 · 아 · 지수 · 수료   ("해지"가 "하+아+지" 로 분해)
#   생활하수도      → 생활 · 하 · 수도 · ᆯ · 수 · 도     ("하수도"가 "하+수도" 로 분해)
#   에스컬레이션    → 에스 · 컬 · 커 · ᆯ · 레 · 이 · 션   (외래어, 통째로 깨짐)
#
# ⚠ `mixed` 는 멀쩡하다 — "수수료" 는 `수수료·수수·료` 로 원형+조각을 제대로 낸다.
#   문제는 **mecab-ko-dic 에 없는 말**이라 미등록어 분해로 떨어지는 것이다.
#   (초안 주석이 "mixed 가 원형을 남긴다"고 일반화해 적었던 것은 틀렸다 —
#    사전에 복합명사로 등재된 것에만 그렇다.)
USER_DICTIONARY_RULES = (
    "중도해지수수료 중도 해지 수수료",
    "생활하수도 생활 하수도",
    "에스컬레이션",
)


def build_settings() -> dict[str, Any]:
    """nori 형태소 분석 + 샤드 1개.

    `decompound_mode: mixed` 는 **사전에 복합명사로 등재된 말**을 원형과 조각 양쪽으로
    남긴다("수수료" → 수수료 · 수수 · 료). 상담 발화는 조각으로, 약관 조항은 원형으로
    쓰이는 일이 많아 한쪽만 남기면 매칭이 끊긴다.

    사전에 **없는** 도메인 용어는 `USER_DICTIONARY_RULES` 로 알려 준다 — 안 그러면 명사가
    용언으로 오분석돼 `하`·`ᆯ` 같은 흔한 토큰이 섞이고, 그 토큰들이 관계없는 문서와 매칭된다.

    **품사 필터(`nori_part_of_speech`)를 토크나이저 바로 뒤에 둔다**(2026-09-22, `decisions/214`).
    없으면 조사·어미·접사가 토큰으로 남아 BM25 순위를 정한다 — `해지` 를 쪼갠 `해` 가 `해주시는` 의
    `해` 와 맞는 식이다(GS-205). **제외 품사는 nori 기본값 그대로다**(E·IC·J·MAG·MAJ·MM·SP·SSC·SSO·SC·
    SE·XPN·XSA·XSN·XSV·UNA·NA·VSV) — `stoptags` 를 따로 주지 않는다. 골든셋을 보며 목록을 고르면
    그 골든셋에 맞춘 것이 되므로, 목록은 미리 정해 둔 기본값에서 움직이지 않는다.
    ⚠ **바꾸면 재적재다** — 분석기는 색인 시점에 적용되므로 기존 인덱스에는 먹지 않는다.

    ⚠ nori 는 `analysis-nori` 플러그인이다. 기본 이미지에 없으면 인덱스 생성이 실패한다
    (`infra/docker-compose.yml` 주석 참고).
    """
    return {
        "number_of_shards": 1,  # BM25 term statistics 가 샤드 단위 — 비교의 교란 변수를 없앤다
        "number_of_replicas": 0,  # 단일 노드 로컬/데모. 복제본을 두면 상태가 yellow 로 남는다
        "analysis": {
            "tokenizer": {
                "kb_nori": {
                    "type": "nori_tokenizer",
                    "decompound_mode": "mixed",
                    "user_dictionary_rules": list(USER_DICTIONARY_RULES),
                },
            },
            "analyzer": {
                "korean": {
                    "type": "custom",
                    "tokenizer": "kb_nori",
                    "filter": ["nori_part_of_speech", "nori_readingform", "lowercase"],
                },
            },
        },
    }


# 임베딩 필드. KoE5 1024차원(`decisions/010`) — **바꾸면 재적재다**(ES 는 dims 변경을 허용하지 않는다).
EMBEDDING_FIELD = "embedding"
EMBEDDING_DIMS = 1024


def build_mapping(*, embedding_dims: int | None = None) -> dict[str, Any]:
    """지금 적재하는 것만 넣는다.

    `doc_id` 는 반드시 `keyword` 다 — 평가 하네스가 이 값을 **정확 일치**로 대조한다
    (`evaluation/metrics/retrieval.py`). `text` 로 분석되면 채점이 조용히 깨진다.

    임베딩(`dense_vector`)은 `embedding_dims` 를 줄 때만 넣는다(2026-09-15, `w4-dense-vector-index`).
    **임베딩 없이도 BM25 인덱스는 그대로 만들어진다** — 운영 서버 파드처럼 torch·모델이 없는 곳에서
    적재할 때(런북 15-1) 검색이 통째로 못 뜨면 안 된다. 유사도는 `cosine` 이다 — KoE5 출력을
    정규화해서 넣으므로 `dot_product` 와 순위가 같지만, 정규화를 빠뜨린 벡터가 들어와도 틀린 값을 내지 않는다.
    """
    properties: dict[str, Any] = {
        "chunk_id": {"type": "keyword"},
        "doc_id": {"type": "keyword"},
        "domain": {"type": "keyword"},
        "doc_type": {"type": "keyword"},
        "title": {"type": "text", "analyzer": "korean"},
        "text": {"type": "text", "analyzer": "korean"},
        "part": {"type": "integer"},
    }
    if embedding_dims is not None:
        properties[EMBEDDING_FIELD] = {
            "type": "dense_vector",
            "dims": embedding_dims,
            "index": True,
            "similarity": "cosine",
        }
    return {"properties": properties}


def embedding_input(chunk: Chunk) -> str:
    """청크 → 임베딩에 넣을 문자열. **제목을 앞에 붙인다** — BM25 가 `title`·`text` 두 필드를 보는 것과
    같은 정보를 쓰게 한다. 한쪽만 제목을 보면 비교가 «검색 방식» 이 아니라 «입력» 차이가 된다."""
    return f"{chunk.title}\n{chunk.text}"


def to_source(chunk: Chunk, embedding: list[float] | None = None) -> dict[str, Any]:
    """청크 → 색인 문서 본문. 두 레이아웃이 같은 문서를 쓴다."""
    doc = {f: getattr(chunk, f) for f in _SOURCE_FIELDS}
    if embedding is not None:
        doc[EMBEDDING_FIELD] = embedding
    return doc


def create_indices(
    client: Any,
    layout: Layout,
    *,
    recreate: bool = False,
    embedding_dims: int | None = None,
    prefix: str = INDEX_PREFIX,
) -> list[str]:
    """레이아웃의 인덱스를 만든다. 이미 있으면 건너뛴다(`recreate=True` 면 지우고 다시).

    client 는 주입받는다 — `elasticsearch` 를 이 모듈이 직접 import 하지 않으므로 패키지가
    없는 환경(CI)에서도 위쪽 순수 함수들과 이 모듈 자체는 import 된다.
    """
    _check_layout(layout)
    created = []
    for name in index_names(layout, prefix=prefix):
        if recreate:
            client.indices.delete(index=name, ignore_unavailable=True)
        if not client.indices.exists(index=name):
            client.indices.create(
                index=name, settings=build_settings(), mappings=build_mapping(embedding_dims=embedding_dims)
            )
            created.append(name)
    return created


def index_chunks(
    client: Any,
    chunks: list[Chunk],
    layout: Layout,
    *,
    embeddings: dict[str, list[float]] | None = None,
    prefix: str = INDEX_PREFIX,
) -> dict[str, int]:
    """청크를 적재하고 인덱스별 문서 수를 돌려준다.

    **재적재가 재현된다** — `_id` 를 `chunk_id` 로 고정한 `index` 연산(upsert)이라 같은 입력을
    몇 번 돌려도 문서 수와 `_id` 집합이 같다. 이게 `w2-kb-index` 의 완료 조건이다.

    `helpers.bulk` 를 쓰지 않는 이유: 지식베이스 전체가 39KB(청크 102개)라 한 번의 `bulk`
    요청에 들어간다. 굳이 `elasticsearch` 를 import 하지 않아도 되고, 실패도 한 응답에서
    다 보인다. 지식베이스가 수 MB 로 커지면 그때 `helpers.bulk` 로 바꾼다.
    """
    _check_layout(layout)
    if not chunks:
        raise ValueError("적재할 청크가 없다")

    if embeddings is not None:
        missing = [c.chunk_id for c in chunks if c.chunk_id not in embeddings]
        if missing:
            # 일부만 벡터가 있으면 kNN 이 그 조항을 **아예 못 찾는다** — 점수가 낮은 게 아니라 후보에서 빠진다.
            raise ValueError(f"임베딩이 없는 청크 {len(missing)}건 — 첫 건: {missing[0]}")

    operations: list[dict[str, Any]] = []
    for c in chunks:
        operations.append({"index": {"_index": index_name_for(c, layout, prefix=prefix), "_id": c.chunk_id}})
        operations.append(to_source(c, embeddings.get(c.chunk_id) if embeddings else None))

    resp = client.bulk(operations=operations, refresh=True)
    if resp.get("errors"):
        failed = [
            item["index"]
            for item in resp["items"]
            if item.get("index", {}).get("error") is not None
        ]
        raise RuntimeError(f"색인 실패 {len(failed)}건 — 첫 건: {failed[0] if failed else '?'}")

    return {name: client.count(index=name)["count"] for name in index_names(layout, prefix=prefix)}


def create_named_index(
    client: Any, name: str, *, recreate: bool = False, embedding_dims: int | None = None
) -> bool:
    """레이아웃과 무관한 이름으로 인덱스 하나를 만든다 — **실험용**(청킹 비교 `w4-chunking-compare`).

    ⚠ 이름이 `callguard-kb-` 로 시작하면 운영 레이아웃의 와일드카드(`callguard-kb-*`)에 섞인다. 막는다.
    """
    if name.startswith(INDEX_PREFIX + "-"):
        raise ValueError(f"실험 인덱스는 {INDEX_PREFIX}- 로 시작할 수 없다: {name}")
    if recreate:
        client.indices.delete(index=name, ignore_unavailable=True)
    if client.indices.exists(index=name):
        return False
    client.indices.create(index=name, settings=build_settings(), mappings=build_mapping(embedding_dims=embedding_dims))
    return True


def index_into(
    client: Any, name: str, chunks: list[Chunk], *, embeddings: dict[str, list[float]] | None = None
) -> int:
    """`index_chunks` 와 같되 인덱스 이름을 직접 받는다. 적재 후 문서 수."""
    if not chunks:
        raise ValueError("적재할 청크가 없다")
    operations: list[dict[str, Any]] = []
    for c in chunks:
        operations.append({"index": {"_index": name, "_id": c.chunk_id}})
        operations.append(to_source(c, embeddings.get(c.chunk_id) if embeddings else None))
    resp = client.bulk(operations=operations, refresh=True)
    if resp.get("errors"):
        raise RuntimeError("색인 실패 — bulk 응답의 errors 가 true")
    return client.count(index=name)["count"]
