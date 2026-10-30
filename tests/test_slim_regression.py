"""슬림 데이터(out/site/data)만으로 §10 경어 검색 회귀 목록이 통과하는지. 브라우저가 하는 순서 그대로: 해시 → 색인 샤드 → 표제어 샤드."""
import json
import unittest
from pathlib import Path

from anikan.common import search_key
from anikan.export.slim import fnv1a
from anikan.normalize.romaji import romaji_key

ROOT = Path(__file__).resolve().parents[1] / "out/site/data"


@unittest.skipUnless((ROOT / "manifest.json").exists(), "out/site/data 없음 — python -m anikan.export.slim 먼저")
class SlimRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.man = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        cls.cache = {}

    def shard(self, kind, n):
        k = (kind, n)
        if k not in self.cache:
            self.cache[k] = json.loads((ROOT / kind / f"{n}.json").read_text(encoding="utf-8"))
        return self.cache[k]

    def lex(self, n):
        return self.shard("lex", n % self.man["shards"]["lex"])[str(n)]

    def lemmas(self, q):
        out = set()
        keys = {search_key(q, "ja"), search_key(q, "ko"), search_key(q), romaji_key(q)}
        for key in keys:
            for hit in self.shard("idx", fnv1a(key) % self.man["shards"]["idx"]).get(key, [])[:20]:
                d = self.lex(hit[0])
                out.add(d["l"])
                for typ in ("hon", "hum", "pol"):                 # 이 표제어가 경어이면 기본형도
                    out.update(r[1] for r in d.get("q", {}).get(typ, []))
        return out

    def test_korean(self):
        for q, want in (("드세요", "먹다"), ("드셨어요", "먹다"), ("주무십니다", "자다"), ("계세요", "있다"), ("가셨습니다", "가다"),
                        ("연세", "나이"), ("진지", "밥")):
            self.assertIn(want, self.lemmas(q), q)

    def test_japanese(self):
        for q, want in (("召し上がりました", "食べる"), ("お書きになる", "書く"), ("食べません", "食べる"), ("學校", "学校")):
            self.assertIn(want, self.lemmas(q), q)
        self.assertTrue({"行く", "来る", "居る"} & self.lemmas("いらっしゃいます"))
        self.assertTrue({"聞く", "訪ねる"} & self.lemmas("伺います"))

    def test_hanzi_and_romaji(self):
        self.assertIn("학교", self.lemmas("學校"))
        self.assertIn("学校", self.lemmas("gakkō"))


if __name__ == "__main__":
    unittest.main()
