#!/usr/bin/env python3
# Requirement: E-1, E-2, B-2, B-4, B-5, D-1, D-2
"""평가 하네스 실행 — 구현된 스포크를 포트에 꽂아 골든셋으로 채점한다 (w2-naive-rag).

    cd infra && docker compose up -d && cd ..
    export ELASTICSEARCH_URL=http://localhost:9200
    .venv/bin/python scripts/run_eval.py                                  # v1-150
    .venv/bin/python scripts/run_eval.py --golden-set golden-set/v1-50.json
    .venv/bin/python scripts/run_eval.py --runs 3                         # 최저치 확인용
    .venv/bin/python scripts/run_eval.py --record                          # 결과를 DB 에 남긴다
    .venv/bin/python scripts/run_eval.py --ollama-url http://localhost:11434   # B-4 카드 생성도 꽂는다(ES 필요)

**이 파일이 평가 쪽 합성 루트다.** `evaluation` 이 `retrieval` 을 직접 import 하면
`ai/.importlinter` 의 module-independence 계약이 깨진다 — 접점은 hub 포트(추상)뿐이어야 하고,
구체 구현을 꽂는 일은 두 모듈 **밖에서** 해야 한다. `server/main.py` 가 요청 경로에 대해
하는 일을 여기서 평가 경로에 대해 한다.

아직 구현되지 않은 스포크는 `None` 으로 남아 "측정 불가 — 모듈 미구현"으로 보고된다.
그 정직성을 우회하지 않는다(절대 원칙 2).

`--runs N` 은 같은 측정을 N 번 돌려 **최저치**를 함께 낸다(절대 원칙 4). 기준선을 고정할
때는 평균이 아니라 그 최저치를 쓴다. 다만 **기록은 이 스크립트가 하지 않는다** — 값 하나에
측정일·커밋·재현 명령·표본 수가 함께 남아야 하고(§5), 그건 `w2-baseline` 티켓의 몫이다.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps")]

from call_guard.adapter.outbound.rule_call_guard_adapter import (  # noqa: E402
    RuleCallGuardAdapter,
)
from compliance.adapter.outbound.rule_compliance_adapter import RuleComplianceAdapter  # noqa: E402
from closure_gate.adapter.outbound.rule_closure_gate_adapter import (  # noqa: E402
    RuleClosureGateAdapter,
)
from evaluation.golden_set import DEFAULT_POSTCALL_SET_PATH, load_golden_set, load_postcall_set  # noqa: E402
from evaluation.harness import NOT_IMPLEMENTED, RETRIEVAL_NO_ENGINE, Ports, run_eval  # noqa: E402
from evaluation.report import print_report  # noqa: E402
from hub.adapter.outbound.postgres.eval_run_repository import (  # noqa: E402
    EvalRunRecord,
    PostgresEvalRunRepository,
)
from masking.adapter.outbound.rule_masking_adapter import (  # noqa: E402
    PARTIAL_PATTERNS,
    SUPPORTED_PATTERNS,
    RuleMaskingAdapter,
)
from pii_ner.adapter.outbound.layered_masking_adapter import (  # noqa: E402
    NER_PATTERNS,
    LayeredMaskingAdapter,
)
from postcall.adapter.outbound.rule_postcall_adapter import RulePostcallAdapter  # noqa: E402
from retrieval.adapter.outbound.es_bm25_retriever import EsBm25Retriever  # noqa: E402
from retrieval.adapter.outbound.es_index import SINGLE_INDEX  # noqa: E402
from voice_signal.adapter.outbound.wav_voice_outlier_adapter import (  # noqa: E402
    WavVoiceOutlierAdapter,
)


def masking_coverage(items, *, ner_enabled: bool = False) -> dict[str, list[str]]:
    """어댑터가 **지원한다고 선언한 패턴**과 **골든셋이 실제로 재는 패턴**을 대조한다.

    **여기서 하는 이유**: 어댑터의 선언(`SUPPORTED_PATTERNS`·`PARTIAL_PATTERNS`)은
    `server/apps/masking/` 에 있고 골든셋은 `evaluation` 이 읽는다. 둘을 동시에 아는 코드는
    양쪽 계약 밖의 **합성 루트**에 있어야 한다 — 이 파일이 그 자리다. 포트를 넓히지 않고
    상수를 읽기만 하므로 `MaskingPort` 계약은 그대로다.

    장민석이 2026-08-27 에 `PARTIAL_PATTERNS` 를 두며 *"완전 지원과 뭉뚱그리면 평가
    하네스가 수치를 해석할 수 없다"* 고 적었다. 그 선언을 실제로 읽는 곳이 없어서
    (`ai/` 에서 grep 0건) 2026-08-28 에 이었다.
    """
    measured = {p.pattern for it in items for p in it.pii_patterns}
    # NER 이 켜져 있으면 P6·P7 은 「규칙 폴백만」이 아니라 「NER + 규칙 두 겹」이다(w5-ner-p6-p7).
    ner = sorted(set(NER_PATTERNS) & measured) if ner_enabled else []
    return {
        "measured": sorted(measured),
        "uncovered": sorted(set(SUPPORTED_PATTERNS) - measured),
        "rule_fallback": [] if ner_enabled else sorted(set(PARTIAL_PATTERNS) & measured),
        "ner_layered": ner,
    }



def _es_client(url: str | None):
    """ES 클라이언트. 없으면 None 을 돌려주고 검색은 "미구현"으로 보고된다.

    설정을 읽는 곳을 스크립트 한 곳으로 모은다 — 어댑터가 환경변수를 직접 읽으면
    테스트에서 갈아끼울 수 없다. `scripts/index_knowledge_base.py` 와 같은 방식이다.
    """
    if not url:
        return None
    try:
        from elasticsearch import Elasticsearch
    except ModuleNotFoundError:
        raise SystemExit("elasticsearch 패키지가 없다:  pip install -r ai/requirements.txt") from None

    api_key = os.environ.get("ELASTICSEARCH_API_KEY") or None
    client = Elasticsearch(url, api_key=api_key) if api_key else Elasticsearch(url)
    if not client.ping():
        raise SystemExit(f"ES 에 붙지 못했다: {url}  (cd infra && docker compose up -d)")
    return client


def build_masking(ner_model_dir: Path | None) -> LayeredMaskingAdapter:
    """C-5 — 규칙(server/apps/masking) 위에 NER(ai/apps/pii_ner)을 얹는다.

    모델 디렉터리가 없거나 `--no-ner` 면 규칙만 도는 어댑터가 된다. **어느 쪽으로 쟀는지는
    리포트의 커버리지 줄이 찍는다** — 같은 「누락 0건」이라도 방식이 다르면 다른 수치다.
    """
    tagger = None
    if ner_model_dir is not None and (ner_model_dir / "config.json").exists():
        from pii_ner.adapter.outbound.koelectra_ner_tagger import KoElectraNerTagger

        tagger = KoElectraNerTagger(ner_model_dir)
    return LayeredMaskingAdapter(RuleMaskingAdapter(), tagger)


RETRIEVERS = ("bm25", "dense", "rerank-dense", "hybrid")


def build_retriever(client, *, index: str, kind: str, device: str | None = None, no_answer_abstain: bool = False):
    """검색 구성. 기본은 **운영과 같은 BM25** 다 — 운영에 임베딩이 켜지기 전까지 하네스 기본값이 운영을 앞서가면
    기록된 수치가 운영 품질로 읽힌다. 나머지는 `decisions/206` 의 비교 대상이다(`scripts/compare_retrievers.py`)."""
    if kind == "bm25":
        return EsBm25Retriever(client, index=index)
    sys.path.insert(0, str(ROOT / "ai"))
    from provider import build_model_retriever

    if kind in ("dense", "rerank-dense"):
        port, layers = build_model_retriever(
            client, index=index, device=device,
            embed_model_dir=ROOT / "models" / "koe5",
            rerank_model_dir=ROOT / "models" / "bge-reranker-v2-m3" if kind == "rerank-dense" else None,
            no_answer_abstain=no_answer_abstain,  # B-6 기권 문턱(decisions/215) — 보류라 기본 꺼짐(운영과 같게)
        )
        expected = ["retrieval_dense"] + (["rerank"] if kind == "rerank-dense" else []) + ["retrieval_cache"]
        if layers != expected:
            raise SystemExit(f"{kind} 를 못 띄웠다(켜진 층 {layers}) — models/ 와 torch 를 확인한다. BM25 로 몰래 재지 않는다")
        return port
    from retrieval.adapter.outbound.es_dense_retriever import EsDenseRetriever
    from retrieval.adapter.outbound.hybrid_retriever import HybridRetriever
    from retrieval.adapter.outbound.koe5_embedder import KoE5Embedder

    dense = EsDenseRetriever(client, KoE5Embedder(ROOT / "models" / "koe5", device=device), index=index)
    return HybridRetriever([EsBm25Retriever(client, index=index), dense])


def build_generation(ollama_url: str | None, model: str | None):
    """B-4 — `server/main.py` 와 같은 프로바이더(`provider.build_generation_provider`)로 만든다. URL 이 없으면 None.

    채점은 하네스가 `evaluation.metrics.generation` 의 규칙으로 한다 — 생성기 필터로 자기를 채점하지 않는다.
    """
    if not ollama_url:
        return None
    sys.path.insert(0, str(ROOT / "ai"))
    from generation.adapter.outbound.ollama_chat import DEFAULT_MODEL
    from provider import build_generation_provider

    return build_generation_provider(ollama_url, model=model or DEFAULT_MODEL)()


def build_ports(client, *, index: str, masking=None, retriever=None, generation=None) -> Ports:
    """구현된 스포크만 꽂는다. 나머지는 None — 하네스가 "미구현"으로 보고한다.

    `masking`·`closure_gate` 는 `server/apps/` 에 산다. 규칙 기반 판정이라 요청 경로에서
    매번 실행되기 때문이다(`server/CLAUDE.md` §0). **여기서 꽂는 것이 계약 위반이 아닌 이유**:
    의존 방향은 `ai → server` 한쪽이고(`server/.importlinter` 계약 2), 이 파일은 두 모듈
    **밖의 합성 루트**라 어느 쪽 계약에도 걸리지 않는다.

    ⚠ **ES 가 없어도 마스킹·F-2 는 채점된다.** 둘 다 외부 의존이 없는 순수 규칙이라
    `ELASTICSEARCH_URL` 없이도 숫자가 나온다 — 검색만 "측정 불가"로 남는다.
    """
    if client is None:
        # ES 가 없을 때도 순수 규칙 두 개는 꽂는다 — 여기서 Ports() 를 비워 돌려주면
        # 이미 구현된 C-5·F-2 가 "미구현"으로 보고돼 측정 가능한 것을 못 재게 된다.
        return Ports(
            masking=masking or RuleMaskingAdapter(),  # C-5 (server/apps/masking [+ ai/apps/pii_ner])
            closure_gate=RuleClosureGateAdapter(),  # F-2 (server/apps/closure_gate)
            call_guard=RuleCallGuardAdapter(),      # C-6 (ai/apps/call_guard)
            compliance=RuleComplianceAdapter(),     # C-1~C-4 (ai/apps/compliance) — 규칙 v1, 수치는 상한
            voice_outlier=WavVoiceOutlierAdapter(),  # D-5 (ai/apps/voice_signal) — 규칙 판정, 외부 의존 없음
            # B-4 — 꽂아도 검색이 없으면 하네스가 「근거 조항이 없다」로 찍는다(생성의 입력이 검색 결과다)
            generation=generation,
            postcall=RulePostcallAdapter(),  # D-1·D-2 — 운영과 같은 규칙 발췌 초안(아래 설명)
        )

    retriever = retriever or EsBm25Retriever(client, index=index)
    return Ports(
        retrieval=retriever,
        masking=masking or RuleMaskingAdapter(),  # C-5 (server/apps/masking [+ ai/apps/pii_ner])
        closure_gate=RuleClosureGateAdapter(),  # F-2 (server/apps/closure_gate)
        call_guard=RuleCallGuardAdapter(),      # C-6 (ai/apps/call_guard) — 규칙 기반, 외부 의존 없음
        compliance=RuleComplianceAdapter(),     # C-1~C-4 (ai/apps/compliance) — 규칙 v1, 골든셋을 본 뒤 썼으므로 수치는 상한
        # D-5 (ai/apps/voice_signal) — WAV 경로 → F0 중앙값 → 화자 기준선(중앙값·MAD). 규칙 판정, 외부 의존 없음.
        # ⚠ 2026-09-21 현재 음성 골든셋이 0건이라 꽂아도 `NO_SAMPLES`(「골든셋에 채점 대상이 없다」)다 —
        #   다산콜DB 는 발화 클립이라 통화 단위 기준선을 못 만든다(`w3-call-temperature`). 「미구현」과
        #   「표본 없음」을 갈라 찍으려고 꽂는다(절대 원칙 10). 통화 단위 + 톤 라벨 골든셋이 생기면 코드 변경 없이 채점된다.
        voice_outlier=WavVoiceOutlierAdapter(),
        # B-4·B-5 (ai/apps/generation) — `--ollama-url` 을 줬을 때만. 모델 서버가 필요하고 한 문항에 모델 호출 1회라
        # 기본값으로 켜지 않는다. 안 꽂으면 하네스가 사유를 붙여 「측정 불가」로 찍는다(`w6-harness-silent-metrics`).
        generation=generation,
        # D-1·D-2 (server/apps/postcall) — **운영 `/close` 가 실제로 쓰는 요약기**다. 운영에는 OLLAMA_URL·GENERATION_MODEL 이 없어
        # `server/main.py::_wire_postcall_model` 이 모델 요약(ai/apps/postcall_summary)을 꽂지 않고 이 규칙 발췌 초안(`decisions/306`)만
        # 돈다 — 그래서 유형은 늘 None 이고 하네스가 「측정 불가 — 유형이 null」로 찍는다(`w6-d2-inquiry-type-null`).
        # 정답은 `golden-set/postcall-v1.json`(통화 단위, `decisions/218`). masking 과 같은 이유로 합성 루트인 여기서 꽂는다.
        postcall=RulePostcallAdapter(),
        # ⚠ trigger 는 **구현이 있는데도 일부러 꽂지 않는다**(IsFinalTrigger, B-1).
        #   TranscriptEvent 에 이벤트 도착 시각이 없어서 발동 시각을 "발화 종료 + STT 지연
        #   상수(346ms)"로 모형화하고 있다. 그대로 채점하면 지연 분포가 상수 하나로 수렴해
        #   p50 = p95 = 346, 적절 발동률 1.0 이 나온다 — **숫자는 나오지만 측정이 아니다.**
        #   측정할 수 없는 것을 측정한 것처럼 쓰지 않는다(절대 원칙 10). 콜 미디에이터가 도착
        #   시각을 실어 보내게 되면 그때 꽂는다. 서버 경로에는 꽂는다(발동 여부는 진짜 판정이다).
        #
        # B-0 도메인 라우팅은 2026-08-28 단일 도메인 전환으로 사라졌다(`decisions/201`).
        # 허브 포트는 계약으로 남아 있고 구현체가 없어 계속 "측정 불가"로 보고된다.
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="골든셋으로 구현된 스포크를 채점한다")
    ap.add_argument("--golden-set", type=Path, default=None, help="기본: golden-set/v1-150.json")
    ap.add_argument("--index", default=SINGLE_INDEX)
    ap.add_argument("--runs", type=int, default=1, help="N 번 돌려 최저치를 함께 낸다 (절대 원칙 4)")
    ap.add_argument("--report-json", type=Path, default=None,
                    help="최저치 리포트를 JSON 으로 남긴다 — scripts/check_baseline.py 의 입력(기준선 게이트)")
    ap.add_argument("--record", action="store_true",
                    help="결과를 PostgreSQL 의 eval_run/eval_result 에 남긴다 (CLAUDE.md §5)")
    ap.add_argument("--ner-model", type=Path, default=ROOT / "models" / "koelectra-ner",
                    help="C-5 P6·P7 NER 모델 디렉터리 (없으면 규칙만)")
    ap.add_argument("--no-ner", action="store_true", help="NER 을 끄고 규칙 마스킹만 잰다 (전/후 대조용)")
    ap.add_argument("--retriever", choices=RETRIEVERS, default="bm25",
                    help="검색 구성 (기본 bm25 = 지금 운영). decisions/206")
    ap.add_argument("--device", default=None, help="임베딩·리랭커 장치 (기본 cpu)")
    ap.add_argument("--ollama-url", default=None,
                    help="B-4 카드 생성을 꽂는다 (없으면 생성은 '측정 불가'). 검색(ES)도 있어야 채점된다")
    ap.add_argument("--generation-model", default=None, help="생성 모델 (기본: generation 어댑터의 DEFAULT_MODEL)")
    ap.add_argument("--postcall-set", type=Path, default=DEFAULT_POSTCALL_SET_PATH,
                    help="D-1·D-2 통화 단위 정답 (기본 golden-set/postcall-v1.json, decisions/218)")
    args = ap.parse_args()

    golden_path = args.golden_set or (ROOT / "golden-set" / "v1-150.json")
    items = load_golden_set(golden_path)
    client = _es_client(os.environ.get("ELASTICSEARCH_URL"))
    if client is None:
        print("⚠ ELASTICSEARCH_URL 이 없다 — 검색은 '측정 불가'로 보고된다.\n")

    masking = build_masking(None if args.no_ner else args.ner_model)
    retriever = build_retriever(client, index=args.index, kind=args.retriever, device=args.device) if client else None
    if client is not None:
        print(f"검색 구성: {args.retriever}")
    generation = build_generation(args.ollama_url, args.generation_model)
    ports = build_ports(client, index=args.index, masking=masking, retriever=retriever, generation=generation)
    postcall_cases = load_postcall_set(args.postcall_set) if args.postcall_set.exists() else []
    reports = [run_eval(items, ports, postcall_cases) for _ in range(args.runs)]
    if client is None:
        # 검색 모듈은 있다 — 없는 것은 이 실행의 ES 다. 「모듈 미구현」이 아니라 그 사유를 싣는다(w2-baseline-gate)
        for report in reports:
            for key in ("retrieval", "no_answer"):
                if report.get(key) == NOT_IMPLEMENTED:
                    report[key] = RETRIEVAL_NO_ENGINE
    print_report(
        reports[0],
        golden_set_path=golden_path,
        masking_coverage=masking_coverage(items, ner_enabled=masking.ner_enabled),
    )

    if args.runs > 1:
        _print_worst(reports)

    if args.report_json:
        # 게이트(`check_baseline.py`)도 최저치를 본다 — 기준선은 평균이 아니다(절대 원칙 4).
        args.report_json.write_text(
            json.dumps(_worst(reports), ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )
        print(f"리포트 JSON: {args.report_json}")

    if args.record:
        # 여러 번 돌렸으면 **최저치**를 남긴다 — 기준선은 평균이 아니다(절대 원칙 4).
        _record(_worst(reports), golden_path, components_label(
            retriever=args.retriever if retriever is not None else "none",  # ES 가 없으면 검색을 안 쟀다
            ner_enabled=masking.ner_enabled,
            generation_model=(args.generation_model or "default") if generation is not None else None))
    return 0


def _git_commit() -> str | None:
    """어느 코드로 잰 값인지. 못 읽으면 None — **지어내지 않는다**(§5).

    ⚠ **워킹트리가 더러우면 뒤에 `-dirty` 를 붙인다**(2026-09-09). 커밋 해시만 남기면
    "이 커밋으로 재현된다"는 뜻이 되는데, 커밋되지 않은 변경으로 잰 값은 그 커밋을
    체크아웃해도 나오지 않는다. 실제로 골든셋 150건 확장을 커밋 전에 재면서 겪었다 —
    HEAD 는 확장 이전인데 수치는 확장 이후 것이었다. 재현 불가를 재현 가능한 것처럼
    적지 않는다(절대 원칙 10).
    """
    r = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                       capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    commit = r.stdout.strip()
    dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"],
                           capture_output=True, text=True)
    if dirty.returncode == 0 and dirty.stdout.strip():
        # `eval_run.git_commit` 이 VARCHAR(40) 이라 40자 해시에 접미어를 붙이면 넘친다.
        # 더러운 상태에서는 **짧은 해시 + `-dirty`** 로 남긴다 — 어차피 그 커밋으로
        # 재현되지 않으므로 전체 해시의 정밀도가 의미를 갖지 않는다. 스키마를 넓히지
        # 않는 이유: `db/schema.sql` 변경은 운영 RDS 마이그레이션을 부른다(정성윤 소관).
        return f"{commit[:7]}-dirty"
    return commit


def components_label(*, retriever: str, ner_enabled: bool, generation_model: str | None) -> str:
    """`eval_run.components` 한 줄 — 실제로 꽂은 구성. VARCHAR(100) 에 들어가게 자른다(w6-server-loose-ends ②)."""
    masking = "rule+ner" if ner_enabled else "rule"
    return f"retriever={retriever}; masking={masking}; generation={generation_model or 'none'}"[:100]


def _record(report: dict, golden_path: Path, components: str | None = None) -> None:
    sys.path.insert(0, str(ROOT / "server"))
    from core.config import load_settings

    settings = load_settings()
    if not settings.postgres_configured:
        raise SystemExit(
            "PostgreSQL 설정이 없어 기록할 수 없다 — .env 의 POSTGRES_* 를 채운다 "
            "(cd infra && docker compose up -d, infra/README.md)"
        )

    import asyncio

    from hub.adapter.outbound.postgres.connection import build_connection_factory

    repo = PostgresEvalRunRepository(build_connection_factory(settings))
    record = EvalRunRecord(
        golden_set_version=golden_path.stem,   # 예: v1-50
        git_commit=_git_commit(),
        error_rate=0.0,                        # STT 오류 주입은 5주차(4.2절) — 지금은 원문 그대로
        executed_by=os.environ.get("USER") or None,
        components=components,
    )
    run_id = asyncio.run(repo.save(record, report))
    print(f"\n기록됨 — eval_run.run_id = {run_id} "
          f"(골든셋 {record.golden_set_version} · 커밋 {(record.git_commit or '?')[:7]})")


def _worst(reports: list[dict]) -> dict:
    """여러 번 실행한 값 중 **최저치**로 리포트를 만든다(절대 원칙 4).

    1회만 돌렸으면 그 리포트 그대로다. 「측정 불가」 문자열은 그대로 나른다 —
    미구현을 숫자로 바꾸지 않는다.
    """
    if len(reports) == 1:
        return reports[0]

    merged: dict = {}
    for section, first in reports[0].items():
        if not isinstance(first, dict):
            merged[section] = first
            continue
        values = [r[section] for r in reports if isinstance(r.get(section), dict)]
        merged[section] = {
            k: (min(v[k] for v in values) if isinstance(v0, (int, float)) and not isinstance(v0, bool)
                else v0)
            for k, v0 in first.items()
        }
    return merged


def _print_worst(reports: list[dict]) -> None:
    """여러 번 실행한 값 중 **최저치**. 기준선은 평균이 아니라 이 값으로 고정한다(절대 원칙 4)."""
    print("\n" + "=" * 60)
    print(f"{len(reports)}회 실행 중 최저치 (기준선은 이 값으로 고정한다 — 절대 원칙 4)")
    worst = _worst(reports)
    for section, result in worst.items():
        if not isinstance(result, dict):
            continue
        print(f"\n[{section}]")
        for k, v in result.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                print(f"  {k}: {v}")


if __name__ == "__main__":
    raise SystemExit(main())
