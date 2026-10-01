# Requirement: E-3
"""재생기 `--save-ws <jsonl>` 로 모은 `/ws` 프레임에서 지연 구간별 p50·p95 를 **표본 수와 함께** 낸다(`w7-latency-budget`).

    python scripts/latency_from_ws.py data/processed/e2e-ws-2026-10-01.jsonl [더 많은 파일…]

읽는 값(추천 메시지 `recommendation` 의 문자열 필드, `decisions/119`):
- `e2e_latency_ms`      발화 종료 → 콜 미디에이터 방송 직전 (STT 미경유 — 합성 통화는 글자 채널이라 ① 구간이 0 이다)
- `internal_latency_ms` 서버 내부(트리거 → 검색 → 생성)
- `retrieval_ms` · `generation_ms`  서버가 실으면 그 구간

값을 지어내지 않는다 — 없는 필드는 n 에 안 센다. 한 통화로 잰 값을 p95 라 부르지 않도록 통화 수도 같이 찍는다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

FIELDS = ("e2e_latency_ms", "internal_latency_ms", "retrieval_ms", "generation_ms")


def percentile(values: list[float], q: float) -> float:
    s = sorted(values)
    if not s:
        return float("nan")
    k = (len(s) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def main(paths: list[str]) -> int:
    samples: dict[str, list[float]] = {f: [] for f in FIELDS}
    calls: set[str] = set()
    frames = fired = 0
    for p in paths:
        for line in Path(p).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            frame = json.loads(line).get("frame")
            msg = json.loads(frame) if isinstance(frame, str) else frame
            if not isinstance(msg, dict) or msg.get("type") != "recommendation":
                continue
            frames += 1
            payload = msg.get("payload") or {}
            if payload.get("call_id"):
                calls.add(str(payload["call_id"]))
            if str(payload.get("fired")) != "true":
                continue  # 발동하지 않은 추천에는 지연값을 싣지 않는다
            fired += 1
            for f in FIELDS:
                v = payload.get(f)
                if v not in (None, ""):
                    samples[f].append(float(v))
    print(f"파일 {len(paths)} · 통화 {len(calls)} · 추천 프레임 {frames} · 발동 {fired}")
    print(f"{'구간':<20}{'n':>5}{'p50':>9}{'p95':>9}{'max':>9}")
    for f in FIELDS:
        v = samples[f]
        if not v:
            print(f"{f:<20}{0:>5}   측정 불가 — 값을 실은 프레임이 없다")
            continue
        print(f"{f:<20}{len(v):>5}{percentile(v, .5):>9.0f}{percentile(v, .95):>9.0f}{max(v):>9.0f}")
    if len(calls) < 5:
        print("⚠ 통화가 5건 미만이다 — p95 를 인용하지 않는다(한 통화로 잰 값은 분포가 아니다)")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1:]))
