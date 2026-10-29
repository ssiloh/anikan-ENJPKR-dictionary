"""표기·읽기 → 표제어 색인. 다른 원본의 단어를 표제어 ID로 푸는 데 쓴다(§5 일본어 표기 해소)."""
from collections import defaultdict

from anikan.common import search_key
from anikan.normalize.romaji import romaji_key, to_romaji

COMPAT = {"adj": {"adj", "adj-na"}, "adj-na": {"adj", "adj-na", "noun"}, "noun": {"noun", "adj-na", "name"},
          "name": {"noun", "name"}, "phrase": {"phrase", "idiom", "proverb"}, "idiom": {"phrase", "idiom"},
          "suffix": {"suffix", "affix"}, "prefix": {"prefix", "affix"}, "affix": {"prefix", "suffix", "affix"}}


def pos_compatible(a, b):
    return not a or not b or a == b or b in COMPAT.get(a, ())


class LangIndex:
    def __init__(self, lang):
        self.lang = lang
        self.by_surface = defaultdict(list)   # key → [lexeme_id]
        self.reading = {}
        self.lemma = {}
        self.pos = {}
        self.nsense = {}
        self.pairs = {}                       # (표기, 읽기) → lexeme_id (첫 항목)
        self.score = {}                       # lexeme_id → 정렬 점수(동음이의어 중 대표를 고르는 데 쓴다)

    def add(self, lex_id, lemma, pos, surfaces, readings=(), nsense=0, score=0):
        self.lemma[lex_id] = lemma
        self.score[lex_id] = score
        self.pos[lex_id] = pos
        self.nsense[lex_id] = nsense
        if readings:
            self.reading[lex_id] = readings[0]
        for s in set(surfaces) | set(readings):
            self.by_surface[search_key(s, self.lang)].append(lex_id)
        for k in list(surfaces) or [None]:
            for r in readings or [None]:
                self.pairs.setdefault((k, r), lex_id)

    def candidates(self, text, pos=None):
        ids = list(dict.fromkeys(self.by_surface.get(search_key(text, self.lang), [])))
        if pos:
            p = [i for i in ids if pos_compatible(pos, self.pos.get(i))]
            if p:
                ids = p
        return ids

    def resolve(self, text, reading=None, pos=None, roman=None):
        """text(+읽기·로마자·품사 힌트)로 표제어 하나. 후보가 여럿이면 읽기·로마자·품사로 좁히고, 못 좁히면 첫 후보."""
        ids = self.candidates(text, pos)
        if not ids:
            return None
        if len(ids) > 1 and reading:
            r = [i for i in ids if search_key(self.reading.get(i, ""), self.lang) == search_key(reading, self.lang)]
            ids = r or ids
        if len(ids) > 1 and roman and self.lang == "ja":
            rk = romaji_key(roman)
            r = [i for i in ids if romaji_key(to_romaji(self.reading.get(i, ""))) == rk]
            ids = r or ids
        return self.best(ids)

    def best(self, ids):
        """점수가 가장 높은 후보(같으면 뜻이 많은 쪽, 그다음 먼저 들어온 쪽)."""
        return max(ids, key=lambda i: (self.score.get(i, 0), self.nsense.get(i, 0))) if ids else None
