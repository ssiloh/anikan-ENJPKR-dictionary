import json
import tempfile
import unittest
from pathlib import Path

from anikan.db import Sink
from anikan.export import slim


class FnvHash(unittest.TestCase):
    def test_known_values(self):
        # FNV-1a 32비트 표준 시험값 — 자바스크립트 구현도 같은 값이 나와야 한다
        self.assertEqual(slim.fnv1a(""), 0x811C9DC5)
        self.assertEqual(slim.fnv1a("a"), 0xE40C292C)
        self.assertEqual(slim.fnv1a("foobar"), 0xBF9CF968)

    def test_feature_code(self):
        self.assertEqual(slim.feature_code(None), "")
        c = slim.feature_code(json.dumps({"tags": ["formal", "polite", "indicative"], "honorific": True, "tense": "past"}))
        self.assertEqual(c, "formal,honorific,past,polite")


class TinyBuild(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            s = Sink(str(d / "t.sqlite"))
            for lid, lang, lemma, reading, pos in (("ja:jmdict:1", "ja", "学校", "がっこう", "noun"), ("ko:krdict:2", "ko", "학교", "학꾜", "noun"),
                                                  ("en:school", "en", "school", None, "noun")):
                s.add("lexeme", id=lid, lang=lang, lemma=lemma, reading=reading, pos=pos, source="x", source_id="1", score=50)
                s.add("form", key=lemma.lower(), surface=lemma, lang=lang, lexeme_id=lid, kind="lemma", source="x")
            s.add("sense", id="ja:jmdict:1#1", lexeme_id="ja:jmdict:1", ord=1, glosses={"en": ["school"]},
                  examples=[{"text": "学校へ行く。", "translation": "I go to school."}])
            s.add("sense", id="en:school#wn:1", lexeme_id="en:school", ord=1, definition="an educational institution")
            s.add("sense", id="en:school#ej:1.1", lexeme_id="en:school", ord=1, definition="学校")
            s.add("link", src="ja:jmdict:1#1", dst="ko:krdict:2", kind="translation", method="hanzi_match", confidence=0.85, sources=["x"])
            s.add("link", src="ja:jmdict:1#1", dst="en:school", kind="translation", method="jmdict_gloss", confidence=0.9, sources=["x"])
            s.add("link", src="ko:krdict:2#1", dst="ja:jmdict:1#1", kind="translation", method="en_pivot", confidence=0.7, sources=["x"])
            s.finish()
            st = slim.run(str(d / "t.sqlite"), d / "out", log=lambda *_: None)
            man = json.loads((d / "out/manifest.json").read_text(encoding="utf-8"))
            key = "学校"
            idx = json.loads((d / "out/idx" / f"{slim.fnv1a(key) % man['shards']['idx']}.json").read_text(encoding="utf-8"))
            n = idx[key][0][0]
            lex = json.loads((d / "out/lex" / f"{n % man['shards']['lex']}.json").read_text(encoding="utf-8"))[str(n)]
            self.assertEqual(lex["i"], "ja:jmdict:1")
            self.assertEqual(lex["s"][0]["x"][0]["t"], "学校へ行く。")
            self.assertEqual([t[1] for t in lex["t"]["ko"]], ["학교"])
            self.assertIn("en", lex["t"])
            # en_pivot은 제외 → 한국어 쪽 번역은 hanzi_match 근거만
            self.assertEqual(lex["t"]["ko"][0][4], "hanzi_match")
            # 영어 표제어는 WordNet 뜻풀이만
            en_n = idx["school"][0][0]
            en = json.loads((d / "out/lex" / f"{en_n % man['shards']['lex']}.json").read_text(encoding="utf-8"))[str(en_n)]
            self.assertEqual([x.get("d") for x in en["s"]], ["an educational institution"])
            self.assertEqual(st["lexemes_included"], {"ja": 1, "ko": 1, "en": 1})


if __name__ == "__main__":
    unittest.main()
