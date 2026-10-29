import unittest

from anikan.common import hanzi_norm, search_key
from anikan.inflect import ja, ko
from anikan.normalize.english import ejdict_candidates
from anikan.normalize.krdict import parse_ja_equiv
from anikan.normalize.romaji import romaji_key, to_romaji


class SearchKey(unittest.TestCase):
    def test_ja_kana_and_kyujitai(self):
        self.assertEqual(search_key("ガッコウ", "ja"), "がっこう")
        self.assertEqual(search_key("學校", "ja"), "学校")

    def test_ko_strips_markers(self):
        self.assertEqual(search_key("가격^표", "ko"), "가격표")
        self.assertEqual(search_key("하ː달되다", "ko"), "하달되다")

    def test_hanzi_norm_matches_japanese_and_korean(self):
        self.assertEqual(hanzi_norm("學校"), hanzi_norm("学校"))

    def test_romaji_key(self):
        self.assertEqual(romaji_key("gakkō"), "gakkou")
        self.assertEqual(to_romaji("がっこう"), "gakkou")
        self.assertEqual(to_romaji("しゅくだい"), "shukudai")


class KoreanGenerator(unittest.TestCase):
    def test_honorific_regular(self):
        c = ko.classify("가다")
        self.assertIn("가셨습니다", [s for s, _ in ko.honorific_forms("가다", c)])
        self.assertIn("가세요", [s for s, _ in ko.honorific_forms("가다", c)])
        self.assertIn("먹으세요", [s for s, _ in ko.honorific_forms("먹다", ko.classify("먹다"))])

    def test_l_drop_and_irregular(self):
        self.assertEqual(ko.honorific_stem("살다", ko.classify("살다")), "사시")
        self.assertEqual(ko.honorific_stem("돕다", ko.classify("돕다", ["도와", "도우니"])), "도우시")
        self.assertEqual(ko.honorific_stem("듣다", ko.classify("듣다", ["들어", "들으니"])), "들으시")
        self.assertEqual(ko.honorific_stem("짓다", ko.classify("짓다", ["지어", "지으니"])), "지으시")
        self.assertEqual(ko.honorific_stem("웃다", ko.classify("웃다", ["웃어", "웃으니"])), "웃으시")

    def test_formal_present(self):
        self.assertEqual(ko.formal_present("가다"), "갑니다")
        self.assertEqual(ko.formal_present("살다"), "삽니다")
        self.assertEqual(ko.formal_present("먹다"), "먹습니다")


class JapaneseGenerator(unittest.TestCase):
    def forms(self, lemma, infl):
        return [s for s, _ in ja.polite_forms(lemma, infl)]

    def test_masu(self):
        self.assertIn("食べません", self.forms("食べる", "v1"))
        self.assertIn("書きます", self.forms("書く", "v5k"))
        self.assertIn("勉強しました", self.forms("勉強する", "vs"))

    def test_te_form_euphony(self):
        self.assertEqual(ja.te_ta("書く", "v5k"), ("書いて", "書いた"))
        self.assertEqual(ja.te_ta("行く", "v5k-s"), ("行って", "行った"))
        self.assertEqual(ja.te_ta("読む", "v5m"), ("読んで", "読んだ"))
        self.assertEqual(ja.te_ta("話す", "v5s"), ("話して", "話した"))

    def test_keigo(self):
        k = {s for s, _, _ in ja.keigo_forms("書く", "v5k")}
        self.assertIn("お書きになる", k)
        self.assertIn("お書きする", k)
        self.assertEqual(ja.keigo_forms("見る", "v1"), [])     # 한 글자 어간은 만들지 않는다
        self.assertIn("ご説明になる", {s for s, _, _ in ja.keigo_forms("説明する", "vs")})


class Extraction(unittest.TestCase):
    def test_krdict_japanese_equivalents(self):
        self.assertEqual(parse_ja_equiv("はし【端】。ふち【縁】"), [("はし", "端"), ("ふち", "縁")])
        self.assertEqual(parse_ja_equiv("ほとり"), [("ほとり", None)])
        self.assertEqual(parse_ja_equiv("(対訳語無し)"), [])

    def test_ejdict_core_words(self):
        self.assertEqual(ejdict_candidates("…を『食べる』;〈食事〉をする"), [("食べる", True)])



class Romaja(unittest.TestCase):
    def test_rr_rules(self):
        from anikan.inflect.ko_romaja import romanize
        cases = {"학교": "hakgyo", "한국": "hanguk", "좋다": "jota", "많이": "mani", "독립": "dongnip", "신라": "silla",
                 "같이": "gachi", "값이": "gapsi", "입학": "ipak", "닭": "dak", "해돋이": "haedoji", "달이": "dari"}
        for k, v in cases.items():
            self.assertEqual(romanize(k), v, k)

if __name__ == "__main__":
    unittest.main()
