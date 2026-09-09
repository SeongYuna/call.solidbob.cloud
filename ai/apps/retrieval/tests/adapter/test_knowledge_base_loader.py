# Requirement: B-2
from pathlib import Path

import pytest

from retrieval.adapter.outbound.knowledge_base_loader import load_chunks
from retrieval.domain.value_objects.chunk import DOMAINS

KB_ROOT = Path(__file__).resolve().parents[4].parent / "knowledge-base"


@pytest.fixture(scope="module")
def chunks():
    return load_chunks(KB_ROOT)


def test_네_도메인이_모두_실린다(chunks):
    assert {c.domain for c in chunks} == set(DOMAINS)


def test_조항_ID가_중복되지_않는다(chunks):
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))


def test_빈_청크가_없다(chunks):
    assert all(c.text.strip() and c.title.strip() for c in chunks)


def test_같은_입력이면_같은_순서로_나온다(chunks):
    assert [c.chunk_id for c in load_chunks(KB_ROOT)] == [c.chunk_id for c in chunks]


@pytest.mark.parametrize("version", ["v1-10.json", "v1-50.json", "v1-150.json"])
def test_골든셋이_참조하는_문서_ID가_전부_실린다(chunks, version):
    """골든셋 채점(Recall@5)의 전제 — 정답 문서가 색인에 없으면 영원히 못 맞힌다.

    2026-08-27: v1-10 만 보고 있어서 v1-50 을 추가했다. 지금은 v1-50 의 14개 ID 도 전부
    실려 있지만, 골든셋이 커질 때 깨진 참조를 잡아 주는 것은 이 테스트뿐이다.
    2026-09-09: 공식 골든셋 v1-150 을 더했다. 옛 판을 함께 두는 이유는 **지식베이스를
    줄일 때 옛 골든셋이 먼저 깨져 알려주기** 때문이다 — 08-28 축소 때 실제로 그랬다.
    """
    import json

    golden = json.loads((KB_ROOT.parent / "golden-set" / version).read_text(encoding="utf-8"))
    items = golden["items"] if isinstance(golden, dict) else golden
    expected = {d for it in items for d in (it.get("expected_doc_ids") or [])}
    distractors = {d for it in items for d in (it.get("distractor_doc_ids") or [])}
    assert expected, f"{version} 에 정답 문서 ID가 없다"
    indexed = {c.doc_id for c in chunks}
    assert expected <= indexed, sorted(expected - indexed)
    # 오답 후보도 실려 있어야 한다 — 색인에 없는 문서는 애초에 헷갈릴 수가 없어
    # "오답 후보"라는 이름값을 못 한다.
    assert distractors <= indexed, sorted(distractors - indexed)


def test_경로가_없으면_실패한다(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_chunks(tmp_path / "없는경로")
