"""§10 4단계 / §11 회귀 목록: 빌드된 out/anikan.sqlite가 있을 때만 돈다."""
import sqlite3
import unittest
from pathlib import Path

from anikan.search.core import search

DB = Path(__file__).resolve().parents[1] / "out/anikan.sqlite"


@unittest.skipUnless(DB.exists(), "out/anikan.sqlite 없음 — python -m anikan.build 먼저")
class HonorificSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = sqlite3.connect(DB)

    def lemmas(self, q, lang=None):
        """검색 결과에 나오는 표제어(경어 표제어와 그 기본형 모두)."""
        out = set()
        for r in search(self.db, q, lang=lang, limit=12, with_translations=False):
            out.add(r["lemma"])
            out.update(b["lemma"] for b in r["base"])
        return out

    # 한국어
    def test_deuseyo(self):
        self.assertIn("먹다", self.lemmas("드세요"))

    def test_deusyeosseoyo(self):
        self.assertIn("먹다", self.lemmas("드셨어요"))

    def test_jumusimnida(self):
        self.assertIn("자다", self.lemmas("주무십니다"))

    def test_gyeseyo(self):
        self.assertIn("있다", self.lemmas("계세요"))

    def test_gasyeotseumnida(self):
        self.assertIn("가다", self.lemmas("가셨습니다"))

    def test_yeonse_nai(self):
        self.assertIn("나이", self.lemmas("연세"))

    def test_jinji_bap(self):
        self.assertIn("밥", self.lemmas("진지"))

    # 일본어
    def test_meshiagarimashita(self):
        self.assertIn("食べる", self.lemmas("召し上がりました"))

    def test_irasshaimasu(self):
        self.assertTrue({"行く", "来る", "居る"} & self.lemmas("いらっしゃいます"))

    def test_okakininaru(self):
        self.assertIn("書く", self.lemmas("お書きになる"))

    def test_ukagaimasu(self):
        self.assertTrue({"聞く", "訪ねる"} & self.lemmas("伺います"))

    def test_tabemasen(self):
        self.assertIn("食べる", self.lemmas("食べません"))

    def test_kyujitai(self):
        self.assertIn("学校", self.lemmas("學校"))

    def test_hanzi_to_korean(self):
        self.assertIn("학교", self.lemmas("學校"))

    # 연결
    def test_translations(self):
        for q, want in (("学校", "학교"), ("犬", "개"), ("勉強", "공부")):
            r = search(self.db, q, lang="ja", limit=3)
            targets = {t["lemma"] for x in r for t in x["translations"]}
            self.assertIn(want, targets, q)


if __name__ == "__main__":
    unittest.main()
