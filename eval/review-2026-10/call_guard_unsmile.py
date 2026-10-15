# Requirement: C-6, E-1
"""심사 질문 27 — 폭언 탐지(어휘 사전 규칙, ai/apps/call_guard)를 **공개 데이터셋**으로 잰다.
데이터: Smilegate UnSmile v1.0 valid (CC-BY-NC-ND 4.0 — 비상업 측정만, 저장소에 싣지 않는다 · data/raw/unsmile/).
⚠ 한계: 온라인 댓글이지 통화 발화가 아니다. 라벨 체계도 다르다(혐오 대상별 + 「악플/욕설」 + clean).
규칙·사전은 고치지 않는다 — 이 데이터를 보고 사전을 고치면 다음 측정이 자기 채점이 된다.
"""
import csv, json, random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps")]
from call_guard.domain.services.detector import detect  # noqa: E402

rows = list(csv.DictReader(open(ROOT / "data/raw/unsmile/unsmile_valid_v1.0.tsv", encoding="utf-8"), delimiter="\t"))
HATE = ["여성/가족", "남성", "성소수자", "인종/국적", "연령", "지역", "종교", "기타 혐오"]
def abusive(d): return [x for x in detect(d) if x.category != "distress"]
stats = {"n": len(rows)}
groups = {"악플/욕설": [r for r in rows if r["악플/욕설"] == "1"],
          "혐오(대상 있음)": [r for r in rows if any(r[h] == "1" for h in HATE) and r["악플/욕설"] != "1"],
          "clean": [r for r in rows if r["clean"] == "1"]}
for g, rs in groups.items():
    hit = [r for r in rs if abusive(r["문장"])]
    stats[g] = {"n": len(rs), "flagged": len(hit), "rate": round(len(hit) / len(rs), 3)}
cats = {}
for r in groups["악플/욕설"]:
    for x in abusive(r["문장"]): cats[x.category] = cats.get(x.category, 0) + 1
stats["악플/욕설_categories"] = cats
random.seed(20261013)
fp = [r["문장"] for r in groups["clean"] if abusive(r["문장"])]
stats["clean_flagged_examples_count"] = len(fp)
print(json.dumps(stats, ensure_ascii=False, indent=1))
(ROOT / "eval/review-2026-10/results/call_guard_unsmile.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))
