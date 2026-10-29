"""gold 세트용 표본 시트(§11)를 뽑는다. 라벨(맞음/틀림/애매)은 사람이 `label` 열에 채운다 — 이 스크립트는 라벨을 만들지 않는다.
python qa/make_gold_sample.py  →  qa/gold_sample.tsv"""
import json
import random
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
random.seed(20261029)
SIZES = {"ja-ko": 300, "en-ja": 100, "en-ko": 100}
BANDS = [(0.5, 0.7), (0.7, 0.85), (0.85, 1.01)]     # 신뢰도 구간별 정밀도를 재기 위한 층화


def sample_pairs(name, n):
    rows = []
    with open(ROOT / "out/pairs" / f"{name}.jsonl", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            for t in r["translations"][:3]:
                rows.append((r, t))
    out = []
    for lo, hi in BANDS:
        pool = [x for x in rows if lo <= x[1]["confidence"] < hi]
        out += random.sample(pool, min(len(pool), n // len(BANDS)))
    return out


def main():
    with open(ROOT / "qa/gold_sample.tsv", "w", encoding="utf-8") as f:
        f.write("set\tsrc_id\tsrc_lemma\tsrc_reading\tdst_id\tdst_lemma\tconfidence\tmethods\tlabel\n")
        for name, n in SIZES.items():
            for r, t in sample_pairs(name, n):
                f.write("\t".join([name, r["id"], r["lemma"], r["reading"] or "", t["id"], t["lemma"], str(t["confidence"]),
                                   ",".join(t["methods"]), ""]) + "\n")
        # 경어 대응 100쌍(한·일 각 50)
        db = sqlite3.connect(ROOT / "out/anikan.sqlite")
        for lang in ("ko", "ja"):
            rows = db.execute("SELECT a.id, a.lemma, b.id, b.lemma, r.type, r.method, r.confidence FROM relation r "
                              "JOIN lexeme a ON a.id = substr(r.src, 1, instr(r.src || '#', '#') - 1) "
                              "JOIN lexeme b ON b.id = substr(r.dst, 1, instr(r.dst || '#', '#') - 1) "
                              "WHERE r.type IN ('honorific_of','humble_of','polite_of') AND a.lang = ?", (lang,)).fetchall()
            for a, al, b, bl, typ, m, c in random.sample(rows, min(50, len(rows))):
                f.write("\t".join(["honorific-" + lang, a, al, "", b, bl, str(c), f"{typ}:{m}", ""]) + "\n")


if __name__ == "__main__":
    main()
