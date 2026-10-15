# Requirement: C-6, E-1
"""발표자료 ▢ 작업 1 — 폭언 분류 AI 가 어휘 사전 규칙(UnSmile valid 재현율 0.188 · 오탐률 0.002)을 **같은 평가 분할**에서 넘는가.

평가 분할: UnSmile v1.0 **valid 원본 그대로**(3,737문장 — 사전 규칙을 쟀던 바로 그 파일, call_guard_unsmile.py).
  채점 대상 = 「악플/욕설」=1 (양성 786) vs 「clean」=1 (음성 935). 혐오 대상만 있는 2,016문장은 라벨 체계가 달라
  사전 측정 때와 똑같이 이진 채점에서 빼고, 참고로 「잡은 비율」만 따로 낸다.
학습 분할: UnSmile v1.0 **공식 train**(같은 이진 규칙). 무작위로 다시 나누지 않았다 — 분할 시드 없음(공식 분할), 비율 = 파일 그대로.
  ⚠ UnSmile 은 CC-BY-NC-ND 4.0 — 여기서 학습한 모델은 **측정 실험용**이다. 저장하지 않고 배포·상업 이용하지 않는다.

모델
  (a) TF-IDF(글자 1~4그램) + 로지스틱 회귀 / 선형 SVM — UnSmile train 으로 학습, CPU
  (b) KcELECTRA-v2(`models/call-guard-kcelectra-v2`) — **UnSmile 을 보지 않은** 배포 후보(kocohub CC-BY-SA + AI Hub 정상 발화,
      decisions/223). 같은 평가 분할에서 추론만 한다
  사전 규칙(운영 `call_guard.domain.services.detector.detect`, distress 제외)은 같은 분할에서 다시 계산한다.

  PYTHONPATH=.venv/lib/python3.12/site-packages <skenv>/bin/python eval/review-2026-10/call_guard_unsmile_train.py
"""
import csv, json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "ai" / "apps"), str(ROOT / "server" / "apps")]
from call_guard.domain.services.detector import detect  # noqa: E402

SEED = 20261015
HATE = ["여성/가족", "남성", "성소수자", "인종/국적", "연령", "지역", "종교", "기타 혐오"]


def load(name):
    return list(csv.DictReader(open(ROOT / f"data/raw/unsmile/unsmile_{name}_v1.0.tsv", encoding="utf-8"), delimiter="\t"))


def binary(rows):
    rs = [r for r in rows if r["악플/욕설"] == "1" or r["clean"] == "1"]
    return [r["문장"] for r in rs], [1 if r["악플/욕설"] == "1" else 0 for r in rs]


def score(y, p):
    tp = sum(a and b for a, b in zip(y, p)); fp = sum((not a) and b for a, b in zip(y, p))
    fn = sum(a and not b for a, b in zip(y, p)); neg = sum(1 for a in y if not a)
    pr = tp / (tp + fp) if tp + fp else 0.0; rc = tp / (tp + fn) if tp + fn else 0.0
    return {"recall": round(rc, 3), "precision": round(pr, 3), "false_positive_rate": round(fp / neg, 3),
            "f1": round(2 * pr * rc / (pr + rc), 3) if pr + rc else 0.0,
            "tp": tp, "fp": fp, "fn": fn, "n": len(y), "positives": sum(y), "negatives": neg}


def lexicon(text):
    return any(x.category != "distress" for x in detect(text))


def main():
    train_rows, valid_rows = load("train"), load("valid")
    Xtr, ytr = binary(train_rows); Xte, yte = binary(valid_rows)
    hate_only = [r["문장"] for r in valid_rows if any(r[h] == "1" for h in HATE) and r["악플/욕설"] != "1"]
    out = {"date": "2026-10-15", "eval_split": "UnSmile v1.0 valid (원본 3,737문장 · 이진 채점 1,721)",
           "train_split": "UnSmile v1.0 train 공식 분할 (이진)", "train_n": len(Xtr), "train_positives": sum(ytr),
           "split_seed": None, "model_seed": SEED, "license": "UnSmile CC-BY-NC-ND 4.0 — 측정 실험용, 모델 미저장·미배포",
           "valid_total_rows": len(valid_rows), "results": {}, "hate_only_flag_rate": {}}

    lex = [lexicon(t) for t in Xte]
    out["results"]["사전 규칙(운영)"] = score(yte, lex)
    out["hate_only_flag_rate"]["사전 규칙(운영)"] = round(sum(map(lexicon, hate_only)) / len(hate_only), 3)

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import LinearSVC
    t0 = time.time()
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(1, 4), min_df=2, sublinear_tf=True)
    A = vec.fit_transform(Xtr); B = vec.transform(Xte); H = vec.transform(hate_only)
    for name, clf in [("TF-IDF + 로지스틱 회귀", LogisticRegression(max_iter=2000, random_state=SEED)),
                      ("TF-IDF + 선형 SVM", LinearSVC(random_state=SEED))]:
        clf.fit(A, ytr); p = [bool(v) for v in clf.predict(B)]
        out["results"][name] = score(yte, p)
        out["results"][name + " ∪ 사전"] = score(yte, [a or b for a, b in zip(p, lex)])
        out["hate_only_flag_rate"][name] = round(float(clf.predict(H).mean()), 3)
    out["tfidf_seconds"] = round(time.time() - t0, 1)

    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    torch.set_num_threads(4)
    md = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "models/call-guard-kcelectra-v2")   # 시드 반복 때 다른 모델 폴더
    tok = AutoTokenizer.from_pretrained(str(md)); m = AutoModelForSequenceClassification.from_pretrained(str(md)).eval()

    @torch.no_grad()
    def pred(texts):
        r = []
        for i in range(0, len(texts), 32):
            enc = tok(texts[i:i + 32], padding=True, truncation=True, max_length=128, return_tensors="pt")
            r += [bool(v) for v in m(**enc).logits.argmax(-1).tolist()]
        return r
    t0 = time.time(); p = pred(Xte)
    out["results"]["KcELECTRA-v2 (UnSmile 미학습 · 배포 후보)"] = score(yte, p)
    out["results"]["KcELECTRA-v2 ∪ 사전"] = score(yte, [a or b for a, b in zip(p, lex)])
    out["hate_only_flag_rate"]["KcELECTRA-v2"] = round(sum(pred(hate_only)) / len(hate_only), 3)
    out["kcelectra_cpu_seconds"] = round(time.time() - t0, 1)

    print(json.dumps(out, ensure_ascii=False, indent=1))
    suffix = "" if len(sys.argv) <= 1 else "_" + Path(sys.argv[1]).name
    (ROOT / f"eval/review-2026-10/results/call_guard_unsmile_train{suffix}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
