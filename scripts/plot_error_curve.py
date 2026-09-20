#!/usr/bin/env python3
# Requirement: E-3, B-2, C-5
"""STT 오류 내성 곡선을 그림 한 장으로 — `measure_error_tolerance.py` 가 낸 JSON 을 읽는다.

    .venv/bin/python scripts/measure_error_tolerance.py --device mps     # 먼저 잰다
    .venv/bin/python scripts/plot_error_curve.py                          # 최신 JSON 으로 그린다
    .venv/bin/python scripts/plot_error_curve.py --json data/processed/error-tolerance/2026-09-15-all.json

기획서 4.2절의 핵심 산출물이다 — 지금까지 숫자 표로만 있었다.

## 이 스크립트가 지키는 것

- **숫자를 만들지 않는다.** 입력 JSON 이 없으면 그리지 않고 멈춘다(절대 원칙 2).
  x 축은 목표 오류율이 아니라 **주입 후 실제로 잰 WER** 이고, y 값은 시드 여러 개 중
  **최저치**(검색) · **최대 누락**(C-5)이다 — `measure_error_tolerance.py` 가 그렇게 저장한다(절대 원칙 4).
- **한 축에 한 척도.** Recall@5(0~1)와 누락 건수(정수)는 **패널을 나눈다.** 두 축을 겹치지 않는다.
- **그림에 한계를 같이 쓴다.** 주입기는 실측 편집의 일부(`meta.unmodeled_share`)를 흉내 내지 못해
  곡선이 낙관 쪽으로 기운다. 그 문장이 그림 안에 들어간다 — 숫자만 잘라 쓰는 것을 막는다.
- 색은 계열 정체성(categorical)에만 쓰고 **순서를 고정**한다. 판정선은 계열 색을 쓰지 않는다(회색 점선).

## 의존성

`matplotlib` 만 더 필요하다(테스트·서버 런타임에는 안 쓰므로 `requirements.txt` 에 넣지 않았다).
없으면 안내만 하고 멈춘다: `pip install matplotlib`
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed" / "error-tolerance"
OUT_DIR = ROOT / "jekyll" / "assets"

# 검증된 기본 팔레트의 categorical 슬롯 1·2·3 (light). 순서를 고정한다 — 계열이 늘어도 돌려쓰지 않는다.
SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a"]
INK_PRIMARY, INK_SECONDARY, INK_MUTED = "#0b0b0b", "#52514e", "#8a8983"
SURFACE, GRID = "#fcfcfb", "#e6e5e0"

# 6.1절 판정선 — 코드가 목표를 「달성」하는 데 쓰지 않는다. 그림에 선으로만 얹는다.
TARGET_CLEAN, TARGET_10PCT = 0.70, 0.60

KOREAN_FONTS = ["Malgun Gothic", "AppleGothic", "Apple SD Gothic Neo", "NanumGothic",
                "Noto Sans CJK KR", "Noto Sans KR", "Source Han Sans KR"]


def pick_font() -> str | None:
    from matplotlib import font_manager
    have = {f.name for f in font_manager.fontManager.ttflist}
    for name in KOREAN_FONTS:
        if name in have:
            return name
    return None


def latest_json() -> Path | None:
    if not DATA_DIR.is_dir():
        return None
    files = sorted(DATA_DIR.glob("*.json"))
    return files[-1] if files else None


def x_of(row: dict) -> float:
    """x 는 «실제로 잰 WER» 이다. 시드마다 달라서 범위로 저장돼 있으니 가운데를 쓴다."""
    lo, hi = row["wer_range"]
    return (float(lo) + float(hi)) / 2


def draw(result: dict, out: Path, font: str | None) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if font:
        plt.rcParams["font.family"] = font
    plt.rcParams["axes.unicode_minus"] = False

    meta = result.get("meta", {})
    panels = [k for k in ("retrieval", "masking") if result.get(k)]
    if not panels:
        raise SystemExit("JSON 에 retrieval·masking 어느 쪽도 없다 — 그릴 것이 없다")

    fig, axes = plt.subplots(1, len(panels), figsize=(6.0 * len(panels), 4.4), dpi=200,
                             facecolor=SURFACE, squeeze=False)
    axes = axes[0]

    for ax, panel in zip(axes, panels):
        ax.set_facecolor(SURFACE)
        series = result[panel]
        for i, (name, rows) in enumerate(series.items()):
            color = SERIES_COLORS[i % len(SERIES_COLORS)]
            xs = [x_of(r) for r in rows]
            ys = [float(r["min_recall_at_5"]) if panel == "retrieval" else int(r["max_miss_count"])
                  for r in rows]
            ax.plot(xs, ys, color=color, linewidth=2, marker="o", markersize=5,
                    markeredgecolor=SURFACE, markeredgewidth=1.2, label=name, zorder=3)
            # 계열이 넷 이하면 끝점에 이름을 직접 단다 — 색만으로 정체성을 주지 않는다
            if len(series) <= 4 and xs:
                ax.annotate(name, (xs[-1], ys[-1]), textcoords="offset points", xytext=(6, 0),
                            va="center", fontsize=8, color=INK_SECONDARY)

        # 끝점 직접 라벨이 잘리지 않게 오른쪽에 여백을 둔다
        all_x = [x_of(r) for rows in series.values() for r in rows]
        if all_x and max(all_x) > min(all_x):
            span = max(all_x) - min(all_x)
            ax.set_xlim(min(all_x) - span * 0.04, max(all_x) + span * 0.18)

        ax.set_xlabel("주입 후 실제로 잰 WER", fontsize=9, color=INK_SECONDARY)
        if panel == "retrieval":
            ax.set_title("검색이 오류를 얼마나 견디나 — Recall@5", fontsize=11, color=INK_PRIMARY, pad=26)
            ax.set_ylabel("Recall@5 (시드 중 최저치)", fontsize=9, color=INK_SECONDARY)
            ax.set_ylim(0, 1.02)
            for y, tag in ((TARGET_CLEAN, f"판정선 {TARGET_CLEAN:.2f} (오류 없음)"),
                           (TARGET_10PCT, f"판정선 {TARGET_10PCT:.2f} (오류 10%)")):
                ax.axhline(y, color=INK_MUTED, linewidth=1, linestyle=(0, (4, 3)), zorder=1)
                ax.annotate(tag, (0.01, y), xycoords=("axes fraction", "data"),
                            xytext=(0, 4), textcoords="offset points", fontsize=7.5, color=INK_MUTED)
        else:
            from matplotlib.ticker import MaxNLocator
            ax.set_title("개인정보 마스킹이 오류를 얼마나 견디나 — 누락 건수", fontsize=11, color=INK_PRIMARY, pad=26)
            ax.set_ylabel("누락 건수 (시드 중 최대)", fontsize=9, color=INK_SECONDARY)
            top = max([int(r["max_miss_count"]) for rows in series.values() for r in rows] + [1])
            ax.set_ylim(-0.35, top + 0.6)
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))     # 누락은 정수다 — 0.5건은 없다
            ax.axhline(0, color=INK_MUTED, linewidth=1, linestyle=(0, (4, 3)), zorder=1)
            ax.annotate("절대 규칙 — 누락 0건", (0.99, 0), xycoords=("axes fraction", "data"),
                        xytext=(0, -12), textcoords="offset points", ha="right",
                        fontsize=7.5, color=INK_MUTED)

        ax.grid(True, color=GRID, linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(GRID)
        ax.tick_params(colors=INK_SECONDARY, labelsize=8)
        # 범례는 그림 영역 밖(제목 아래)에 가로로 — 안에 두면 곡선·기준선 설명과 겹친다
        ax.legend(frameon=False, fontsize=8, labelcolor=INK_SECONDARY, ncol=len(series),
                  loc="lower center", bbox_to_anchor=(0.5, 1.0), handlelength=1.6,
                  columnspacing=1.6, borderpad=0)

    unmodeled = meta.get("unmodeled_share")
    caveat = ("주입기가 실측 STT 오류의 일부를 흉내 내지 못한다"
              + (f"(흉내 못 내는 몫 {float(unmodeled) * 100:.1f}%)" if unmodeled is not None else "")
              + " — 같은 WER 에서 실제보다 덜 파괴적이라 이 곡선은 낙관 쪽으로 기운다.")
    stamp = " · ".join(str(meta.get(k)) for k in ("date", "commit", "golden_set") if meta.get(k))
    # 계열이 빠진 이유를 그림에 남긴다 — 「안 쟀다」와 「잴 수 없었다」는 읽는 사람에게 다른 정보다
    skipped = meta.get("skipped") or []
    if skipped:
        fig.text(0.01, 0.078, "이 측정에서 빠진 계열(모델 파일이 없는 머신): " + " / ".join(skipped),
                 fontsize=8, color=INK_SECONDARY)
    fig.text(0.01, 0.045, caveat, fontsize=8, color=INK_SECONDARY)
    fig.text(0.01, 0.012, f"{stamp} · 시드 {meta.get('seeds')} · {meta.get('command', '')}",
             fontsize=7, color=INK_MUTED)
    fig.subplots_adjust(left=0.075, right=0.975, top=0.86, bottom=0.25, wspace=0.26)

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=SURFACE)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", type=Path, default=None, help="기본: data/processed/error-tolerance/ 의 최신 파일")
    ap.add_argument("--out", type=Path, default=None, help="기본: jekyll/assets/error-tolerance-<날짜>.png")
    args = ap.parse_args()

    try:
        import matplotlib  # noqa: F401
    except ModuleNotFoundError:
        print("matplotlib 이 없다 — `pip install matplotlib` 후 다시 실행한다.", file=sys.stderr)
        return 1

    src = args.json or latest_json()
    if src is None or not src.exists():
        print(f"입력 JSON 이 없다: {src or DATA_DIR}\n"
              "  먼저 재어야 한다 — scripts/measure_error_tolerance.py\n"
              "  (없는 숫자를 그리지 않는다 — 절대 원칙 2)", file=sys.stderr)
        return 1

    result = json.loads(src.read_text(encoding="utf-8"))
    font = pick_font()
    if font is None:
        print("⚠ 한글 글꼴을 못 찾았다 — 라벨이 네모로 나온다. 맑은 고딕·애플고딕·나눔고딕 중 하나를 깔면 된다.",
              file=sys.stderr)

    out = args.out or (OUT_DIR / f"error-tolerance-{result.get('meta', {}).get('date', 'undated')}.png")
    path = draw(result, out, font)
    print(f"그렸다: {path}")
    print(f"  입력: {src}")
    print(f"  글꼴: {font or '(한글 글꼴 없음)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
