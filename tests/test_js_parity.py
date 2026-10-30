"""web/keys.js가 파이썬과 같은 검색 열쇠·해시를 내는지: 손으로 고른 입력 + 실제 색인의 표기 무작위 표본을 node로 대조한다."""
import json
import random
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path

from anikan.common import kyujitai_map, search_key
from anikan.export.slim import fnv1a
from anikan.normalize.romaji import romaji_key

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "out/anikan.sqlite"
HAND = ["学校", "學校", "ガッコウ", "がっこう", "ｶﾞｯｺｳ", "ＡＢＣ　ｄｅｆ", "Gakkō", "shin'ichi", "Ōsaka", "ōkii", "드세요", "하ː달되다", "가격^표", "가격 표",
        "召し上がりました", "お書きになる", "食べません", "ファイル", "ヴァイオリン", "ー", "a-b・c", "İstanbul", "ΣΑΣ", "ǅ", "Ǆ", "\u0085x", "﻿x", "x　y",
        "カ゛", "ｳﾞ", "㈱", "ﬁ", "①②", "Å", "é", "é", "한글", "ᄒᆞᆫ", "", " ", "  \t", "國", "體", "會", "廣", "gakkou", "O'Brien"]


@unittest.skipUnless(shutil.which("node"), "node 없음")
class JsParity(unittest.TestCase):
    def test_keys_match_python(self):
        qs = list(HAND)
        if DB.exists():
            db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
            rows = [r[0] for r in db.execute("SELECT surface FROM form WHERE rowid % 450 = 7")]
            random.Random(1).shuffle(rows)
            qs += rows[:7000]
        cases = []
        for q in qs:
            cases.append({"q": q, "ja": search_key(q, "ja"), "ko": search_key(q, "ko"), "en": search_key(q), "romaji": romaji_key(q),
                          "h": fnv1a(search_key(q, "ja"))})
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "cases.json").write_text(json.dumps(cases, ensure_ascii=False), encoding="utf-8")
            (d / "kyu.json").write_text(json.dumps(kyujitai_map(), ensure_ascii=False), encoding="utf-8")
            r = subprocess.run(["node", str(ROOT / "tests/js/parity.mjs"), str(d / "cases.json"), str(d / "kyu.json")],
                               capture_output=True, text=True, check=True)
        out = json.loads(r.stdout)
        self.assertEqual(out["n_bad"], 0, out["mismatches"])
        self.assertEqual(out["checked"], len(cases))


if __name__ == "__main__":
    unittest.main()
