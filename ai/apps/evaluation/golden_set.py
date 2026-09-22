# Requirement: E-1
"""골든셋(JSON)을 로드해서 항목별 타입으로 돌려준다.

골든셋 자체는 이 저장소의 golden-set/v1-10.json이며, 스펙은 golden-set/README.md
(= 데이터 확보 계획 5.3절)와 동일하다. 이 모듈은 그 JSON을 채점 코드가 쓰기 편한
형태로만 파싱한다 — 정답을 스스로 만들어내지 않는다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_GOLDEN_SET_PATH = (
    Path(__file__).resolve().parents[3] / "golden-set" / "v1-150.json"
)


@dataclass(frozen=True)
class ComplianceViolation:
    type: str
    phrase: str
    expected_alternative_source: str | None = None


@dataclass(frozen=True)
class PiiPattern:
    pattern: str  # P1~P7
    raw_span: str
    masked_expected: bool


@dataclass(frozen=True)
class CallGuardCase:
    """C-6 — **고객** 발화의 폭언·위기 신호. C-1~C-4(상담원 발화)와 방향이 반대다.

    `type` 은 `DASAN-MANUAL-5.1~5.4` 가 나눈 대응 갈래를 그대로 쓴다. 특히 `distress`
    (자해·극단적 선택 암시)는 **폭언과 다르게 다뤄야 하므로** 같은 라벨로 뭉치지 않는다
    (5.4조 — 통화를 끊지 않고 전문 기관으로 연결한다).
    """

    type: str  # "insult" | "threat" | "sexual" | "distress"
    phrase: str
    source: str | None = None


@dataclass(frozen=True)
class F2Case:
    procedure: str  # 필요서류 조항 ID (DASAN-TERM-x.y) — 2026-09-14 `closure_type` 에서 바뀌었다(`decisions/305`)
    evidence: dict[str, bool]
    expected_verdict: str  # "complete" | "incomplete"
    expected_missing: list[str]
    source: str | None = None


@dataclass(frozen=True)
class CallTemperatureGoldenCase:
    """D-5 통화 온도 — **통화 1건·화자 1명**의 발화별 음성과 톤 라벨(`_project/decisions/203`).

    `expected_outliers`(튀어야 할 발화)·`calm`(튀면 안 되는 발화)은 **`segment_id`** 로 적는다 —
    `voice_signal` 이 돌려주는 `SegmentOutlier.segment_id` 와 같은 키다. 어느 쪽에도 없는 발화는
    「애매한 턴」으로 채점에서 빠진다(`metrics/call_temperature.py`). 정답은 사람이 **음성을 듣고**
    붙인 라벨이고, 특징값(F0·에너지)은 싣지 않는다 — 우리 추출기가 낸 값을 정답에 적어 두면
    추출기를 고칠 때마다 정답이 낡는다. 오디오는 저작권·개인정보가 해결된 출처뿐이다(절대 원칙 7).

    ⚠ **2026-09-21 현재 0건이다.** 다산콜DB 는 발화 클립이라 통화 단위 기준선을 만들 수 없다
    (`w3-call-temperature`). 이 형식은 그 골든셋이 생겼을 때 코드 변경 없이 채점되게 하려고 먼저 둔다.
    """

    speaker: str  # "customer" | "agent"
    utterances: list[tuple[int, str]]  # (segment_id, 오디오 경로 — JSON 파일 위치 기준 상대경로를 절대경로로 푼 것)
    expected_outliers: list[int]
    calm: list[int]
    source: str | None = None

    def __post_init__(self) -> None:
        if self.speaker not in ("customer", "agent"):
            raise ValueError(f"'{self.speaker}' 는 화자가 아닙니다 (customer | agent)")
        ids = [sid for sid, _ in self.utterances]
        if len(ids) != len(set(ids)):
            raise ValueError("call_temperature.utterances 에 segment_id 가 겹친다")
        overlap = set(self.expected_outliers) & set(self.calm)
        if overlap:
            raise ValueError(f"한 발화가 「튀어야 함」과 「차분함」 양쪽에 있다: {sorted(overlap)}")
        unknown = (set(self.expected_outliers) | set(self.calm)) - set(ids)
        if unknown:
            raise ValueError(f"라벨이 가리키는 segment_id 가 utterances 에 없다: {sorted(unknown)}")


@dataclass(frozen=True)
class GoldenItem:
    id: str
    module: str
    domain: str | None = None  # "finance" | "dasan" | "shopping" | "health"
    customer_utterance: str | None = None
    agent_utterance: str | None = None
    utterance_end_ms: int | None = None
    # 이 발화 앞에 오간 말. **검색 질의를 만들 때 함께 넣는다.**
    # 2026-09-09 AI Hub 다산 실제 발화를 훑다가 넣었다 — 서류 문의의 상당수가
    # "필요한 서류가 있나요?"·"어떤서류가 필요한가요?" 처럼 **단독으로는 무엇에 대한
    # 질문인지 알 수 없는 중간 턴**이다. 이런 발화를 그대로 질의로 쓰면 검색이 실패하는
    # 것이 당연해지고, 우리가 재는 것이 "검색 성능"이 아니라 "발화가 자족적인가"가 된다.
    # `decisions/201` 이 B 를 「대화 맥락으로 절차를 판정」이라고 적은 그대로다.
    context_utterances: list[str] = field(default_factory=list)
    trigger_examples: list[dict] = field(default_factory=list)
    expected_doc_ids: list[str] = field(default_factory=list)
    distractor_doc_ids: list[str] = field(default_factory=list)
    compliance_violation: ComplianceViolation | None = None
    pii_patterns: list[PiiPattern] = field(default_factory=list)
    f2_case: F2Case | None = None
    # C-6 콜 가드 — 고객 발화의 폭언·위기 신호. 없으면 None(정상 발화).
    call_guard: "CallGuardCase | None" = None
    # D-5 통화 온도 — 통화 단위 음성 + 톤 라벨. 없으면 None(기존 항목 전부).
    call_temperature: CallTemperatureGoldenCase | None = None
    notes: str | None = None


def _call_temperature_case(raw: dict, base_dir: Path) -> CallTemperatureGoldenCase:
    """JSON 의 `call_temperature` → 케이스. 오디오 경로는 **골든셋 JSON 이 있는 디렉터리 기준**으로 푼다 —
    음성은 `data/`(gitignore) 아래에 있어 저장소 밖 절대경로를 적을 수 없고, 실행 위치에 따라 달라지면 안 된다."""
    utterances = []
    for u in raw["utterances"]:
        audio = Path(u["audio"])
        if not audio.is_absolute():
            audio = (base_dir / audio).resolve()
        utterances.append((int(u["segment_id"]), str(audio)))
    return CallTemperatureGoldenCase(
        speaker=raw["speaker"],
        utterances=utterances,
        expected_outliers=[int(i) for i in raw.get("expected_outliers", [])],
        calm=[int(i) for i in raw.get("calm", [])],
        source=raw.get("source"),
    )


def load_golden_set(path: Path | str = DEFAULT_GOLDEN_SET_PATH) -> list[GoldenItem]:
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    items: list[GoldenItem] = []
    for entry in raw["items"]:
        cv = entry.get("compliance_violation")
        f2 = entry.get("f2_case")
        cg = entry.get("call_guard")
        ct = entry.get("call_temperature")
        items.append(
            GoldenItem(
                id=entry["id"],
                module=entry["module"],
                domain=entry.get("domain"),
                customer_utterance=entry.get("customer_utterance"),
                agent_utterance=entry.get("agent_utterance"),
                utterance_end_ms=entry.get("utterance_end_ms"),
                context_utterances=entry.get("context_utterances", []),
                trigger_examples=entry.get("trigger_examples", []),
                expected_doc_ids=entry.get("expected_doc_ids", []),
                distractor_doc_ids=entry.get("distractor_doc_ids", []),
                compliance_violation=(
                    ComplianceViolation(**cv) if cv else None
                ),
                pii_patterns=[
                    PiiPattern(**p) for p in entry.get("pii_patterns", [])
                ],
                f2_case=(F2Case(**f2) if f2 else None),
                call_guard=(CallGuardCase(**cg) if cg else None),
                call_temperature=(_call_temperature_case(ct, path.parent) if ct else None),
                notes=entry.get("notes"),
            )
        )
    return items


# ── D-1·D-2 통화 후 처리 — 별도 파일 `golden-set/postcall-v1.json` (`w6-postcall-golden-cases`, `decisions/218`) ──
#
# `v1-150.json` 은 **발화 한 줄** 단위라 통화 하나를 담을 자리가 없다. 그래서 통화 단위 정답은 따로 두고, 발화는
# 합성 대본(`scripts/persona_sim/dasan-v0/SYN-*.json`)을 **경로로 가리킨다** — 대본을 복사해 두면 대본이 고쳐질 때
# 정답과 발화가 조용히 갈라진다. 대신 `turn_count` 를 함께 적어 대본이 바뀌면 로드에서 멈춘다.

DEFAULT_POSTCALL_SET_PATH = DEFAULT_GOLDEN_SET_PATH.parent / "postcall-v1.json"


@dataclass(frozen=True)
class PostcallGold:
    id: str
    script_id: str
    turns: list[tuple[int, str, str]]  # (seq, speaker, text) — 대본 순서 그대로
    inquiry_type: str
    key_items: tuple  # tuple[metrics.postcall.KeyItem, ...]


def load_postcall_set(path: Path | str = DEFAULT_POSTCALL_SET_PATH) -> list[PostcallGold]:
    """통화 후 처리 정답을 읽고, 가리키는 대본에서 발화를 채운다. 대본 경로는 **저장소 루트 기준**이다."""
    from .metrics.postcall import KeyItem

    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    repo_root = path.resolve().parent.parent
    catalogue = set(raw["type_catalogue"]["types"])
    out: list[PostcallGold] = []
    for entry in raw["items"]:
        script = json.loads((repo_root / entry["script"]).read_text(encoding="utf-8"))
        if script["id"] != entry["script_id"]:
            raise ValueError(f"{entry['id']}: 대본 id {script['id']} ≠ {entry['script_id']}")
        if len(script["turns"]) != entry["turn_count"]:
            raise ValueError(
                f"{entry['id']}: 대본 {entry['script_id']} 의 턴 수가 {len(script['turns'])} 로 바뀌었다"
                f"(라벨 당시 {entry['turn_count']}) — 정답을 다시 확인한다"
            )
        if entry["inquiry_type"] not in catalogue:
            raise ValueError(f"{entry['id']}: 유형 {entry['inquiry_type']!r} 이 유형표에 없다")
        items = tuple(
            KeyItem(id=f"{entry['id']}.{k['id']}", kind=k["kind"], label=k["label"], forms=tuple(k["forms"]))
            for k in entry["key_items"]
        )
        ids = [k.id for k in items]
        if len(ids) != len(set(ids)):
            raise ValueError(f"{entry['id']}: 핵심 항목 id 가 겹친다")
        out.append(
            PostcallGold(
                id=entry["id"],
                script_id=entry["script_id"],
                turns=[(int(t["seq"]), t["speaker"], t["text"]) for t in script["turns"]],
                inquiry_type=entry["inquiry_type"],
                key_items=items,
            )
        )
    return out
