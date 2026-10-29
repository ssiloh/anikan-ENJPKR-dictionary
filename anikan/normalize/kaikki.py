"""kaikki 일본어·한국어 → lexeme · sense · form · relation.
- 같은 표기·품사의 JMdict/한국어기초사전 표제어가 있으면 그 표제어에 합치고(활용 색인·관계만 더함), 없으면 새 표제어.
- 활용형 표제어(`polite form of ある`, `hanja form of 학교`)는 표제어를 만들지 않고 기본형으로 가는 form 줄로."""
import re
from collections import defaultdict

from anikan.common import HANGUL, KANA, WORK, hanzi_norm, read_jsonl, search_key
from anikan.lexindex import pos_compatible
from anikan.normalize.maps import map_pos, pick_register, region_map, register_map
from anikan.normalize.romaji import romaji_key

SKIP_POS = {"soft-redirect", "romanization", "character", "syllable", "punct", "symbol"}
KEEP_FORM_TAGS = {
    "ja": {"negative", "past", "formal", "polite", "conjunctive", "continuative", "volitional", "potential"},
    "ko": {"polite", "formal", "past", "future", "infinitive", "imperative", "hortative", "honorific", "conjunctive"},
}
VARIANT_TAGS = {"kyūjitai", "shinjitai", "alternative", "kanji", "hiragana", "katakana", "hangeul", "hanja"}
HONORIFIC_GLOSS = re.compile(
    r"\b(honorific|humble|respectful|deferential|polite)\b(?:\s+\w+){0,2}?\s+of\s+([^\s(,;:\"“”\[\]]+)")
OR_TARGET = re.compile(r"\bor\s+([^\s(,;:\"“”\[\]]+)\s*\(")
HON_TYPE = {"honorific": "honorific_of", "respectful": "honorific_of", "humble": "humble_of",
            "deferential": "humble_of", "polite": "polite_of"}
FORM_OF_KIND = re.compile(r"(form|imperfective|continuative|conjunctive|indicative|imperative|hortative|present|past|"
                          r"negative|polite|formal|informal|volitional|potential|passive|causative|conditional|"
                          r"attributive|stem|interrogative|sequential|infinitive)\b")


def features_from_tags(tags, gloss=""):
    t = set(tags)
    text = gloss.lower()
    f = {"tags": sorted(t)}
    if t & {"polite", "formal"} or "polite" in text:
        f["politeness"] = "polite" if ("polite" in t or "polite" in text) else "formal"
    if "honorific" in t or "honorific" in text:
        f["honorific"] = True
    if "past" in t or " past" in text:
        f["tense"] = "past"
    elif "future" in t:
        f["tense"] = "future"
    if "negative" in t or "negative" in text:
        f["polarity"] = "neg"
    return f


class Normalizer:
    def __init__(self, sink, lang, index, ja_index=None, stats=None):
        self.sink, self.lang, self.index = sink, lang, index
        self.stats = stats if stats is not None else {}
        self.rm = register_map()
        self.regm = region_map()
        self.counter = defaultdict(int)
        self.pending_rel = []          # (src, 단어, type, pos힌트)
        self.pending_forms = []        # form_of 해소를 지연: (surface, base, tags, gloss, kind_hint)
        self.entry_lexeme = {}         # (word, pos_raw, etym_no) → lexeme_id  (번역·삼각 연결용)
        self.merged = 0
        self.created = 0

    def inc(self, k, n=1):
        self.stats[f"{self.lang}_{k}"] = self.stats.get(f"{self.lang}_{k}", 0) + n

    # --- 표제어 만들기 / 합치기 ---
    def find_merge(self, word, pos):
        """합칠 기존 표제어: 표기가 같은 후보를 먼저, 없으면 후보가 하나뿐일 때만(동형이의어 오합침 방지)."""
        cands = self.index.candidates(word, pos)
        same = [c for c in cands if self.index.lemma.get(c) == word]
        if same:
            return self.index.best(same)
        return cands[0] if len(cands) == 1 else None

    def add_forms(self, lex_id, e, new_lexeme):
        agg = defaultdict(set)
        lang = self.lang
        keep = KEEP_FORM_TAGS[lang]
        for f in e["forms"]:
            tags = set(f["tags"])
            surf = f["form"]
            if "romanization" in tags or "Rōmaji" in tags:
                key = romaji_key(surf)
                if key:
                    self.sink.add("form", key=key, surface=surf, lang=lang, lexeme_id=lex_id, kind="romaji",
                                  features=None, via=None, source="kaikki")
                continue
            if tags & VARIANT_TAGS and not (tags & keep):
                kind = "hanzi" if "hanja" in tags else "variant"
                key = search_key(surf, lang)
                if key and surf != e["word"]:
                    self.sink.add("form", key=key, surface=surf, lang=lang, lexeme_id=lex_id, kind=kind,
                                  features={"tags": sorted(tags)}, via=None, source="kaikki")
                continue
            if tags & keep and surf != e["word"]:
                agg[surf] |= tags
        for surf, tags in agg.items():
            key = search_key(surf, lang)
            if not key:
                continue
            kind = "honorific_inflection" if "honorific" in tags else "inflection"
            self.sink.add("form", key=key, surface=surf, lang=lang, lexeme_id=lex_id, kind=kind,
                          features=features_from_tags(tags), via=None, source="kaikki")
            self.inc("inflection_forms")

    def sense_rows(self, lex_id, e, start=1):
        regs = []
        for n, s in enumerate(e["senses"], start):
            tags = s.get("tags", [])
            reg = pick_register([self.rm[("kaikki", t)] for t in tags if ("kaikki", t) in self.rm])
            regs.append(reg)
            labels = {}
            if s.get("topics"):
                labels["domain"] = s["topics"]
            regions = [self.regm[("kaikki", t)] for t in tags if ("kaikki", t) in self.regm]
            if regions:
                labels["region"] = regions
            usage = [t for t in tags if ("kaikki", t) not in self.rm and ("kaikki", t) not in self.regm]
            if usage:
                labels["usage"] = usage
            ex = [{"text": x["text"], "translation": x["en"], "lang": self.lang, "source": "kaikki"} for x in s.get("examples", [])]
            gl = s.get("glosses", [])
            self.sink.add("sense", id=f"{lex_id}#{n}", lexeme_id=lex_id, ord=n, definition="; ".join(gl) or None,
                          def_lang="en", glosses={"en": gl}, register=reg, labels=labels or None, examples=ex or None,
                          extra={"raw": s.get("raw"), "tags": tags})
            self.inc("sense")
        return regs

    def collect_relations(self, lex_id, e, sense_ids):
        """synonyms/antonyms/related/derived + 경어 뜻풀이 → 지연 해소 목록."""
        def add(src, words, typ):
            for w in words:
                w = re.sub(r"\(.*?\)$", "", w).strip()
                if w:
                    self.pending_rel.append((src, w, typ))
        for k, t in (("synonyms", "synonym"), ("antonyms", "antonym"), ("related", "see_also"), ("derived", "derived")):
            add(lex_id, e.get(k, []), t)
        sids = sense_ids or [lex_id] * len(e["senses"])   # 합친 표제어는 뜻을 더하지 않으므로 표제어 수준
        for sid, s in zip(sids, e["senses"]):
            for k, t in (("synonyms", "synonym"), ("antonyms", "antonym"), ("related", "see_also"), ("derived", "derived")):
                add(sid, s.get(k, []), t)
            for g in s.get("glosses", []):
                m = HONORIFIC_GLOSS.search(g)
                if m and not s.get("form_of"):
                    targets = [m.group(2)] + OR_TARGET.findall(g[m.end():])
                    for tgt in targets:
                        self.pending_rel.append((sid, tgt, HON_TYPE[m.group(1)]))
                    self.inc("honorific_gloss")

    def level_of(self, e):
        return None

    def run(self, path):
        lang = self.lang
        for e in read_jsonl(path):
            self.inc("entries")
            pos_raw = e["pos"]
            if pos_raw == "soft-redirect":
                # 읽기·이표기 → 가리키는 표제어들 (동음이의어 모두가 정당한 대상)
                for tgt in e.get("redirects", []):
                    self.pending_forms.append((e["word"], tgt, [], "", "variant", None))
                self.inc("redirect_entries")
                continue
            if pos_raw in SKIP_POS:
                self.inc("skipped_" + pos_raw.replace("-", "_"))
                continue
            senses = e["senses"]
            fo = [w for s in senses for w in s.get("form_of", []) if w]
            alt = [w for s in senses for w in s.get("alt_of", []) if w]
            tags0 = {t for s in senses for t in s.get("tags", [])}
            pos = map_pos("kaikki", pos_raw) or None
            if fo or alt:
                # 활용형·이표기 → 기본형으로 가는 색인 줄 (지연)
                base = (fo or alt)[0]
                gloss = " ".join(g for s in senses for g in s.get("glosses", []))
                hanja = "hanja" in tags0
                self.pending_forms.append((e["word"], base, sorted(tags0), gloss, "hanzi" if hanja else
                                           ("variant" if (alt or "alternative" in tags0 or not FORM_OF_KIND.search(gloss)) else "inflection"), pos))
                self.inc("form_of_entries")
                continue
            word = e["word"]
            target = self.find_merge(word, pos)
            etym = e.get("etymology_number") or 0
            if target:
                lex_id = target
                self.merged += 1
                self.inc("merged")
                self.add_forms(lex_id, e, False)
                # 합친 표제어에는 뜻을 더하지 않으므로 관계는 표제어 수준으로만 담는다
                self.collect_relations(lex_id, e, [])
            else:
                self.counter[(word, pos_raw)] += 1
                lex_id = f"{lang}:kaikki:{word}:{pos_raw}:{self.counter[(word, pos_raw)]}"
                self.created += 1
                self.inc("created")
                hanzi = next((f["form"] for f in e["forms"] if "hanja" in f["tags"]), None) if lang == "ko" else (
                    word if re.search(r"[一-鿿]", word) else None)
                reading = None
                for s in e.get("sounds", []):
                    v = s.get("hangeul") if lang == "ko" else s.get("other")
                    if v and ((lang == "ko" and HANGUL.search(v)) or (lang == "ja" and KANA.search(v))):
                        reading = v.strip("[]")
                        break
                if lang == "ja" and reading is None and KANA.search(word) and not re.search(r"[一-鿿]", word):
                    reading = word
                regs = [pick_register([self.rm[("kaikki", t)] for t in s.get("tags", []) if ("kaikki", t) in self.rm]) for s in senses]
                keigo = [r for r in regs if r in ("honorific", "humble", "polite")]
                lex_reg = keigo[0] if keigo else (regs[0] if regs and all(r == regs[0] for r in regs) else None)
                infl = None
                if lang == "ja" and pos == "verb":
                    infl = "v1" if "ichidan" in tags0 else "v5" if "godan" in tags0 else "vs" if "suru" in tags0 else None
                self.sink.add("lexeme", id=lex_id, lang=lang, lemma=word, reading=reading, hanzi=hanzi,
                              hanzi_norm=hanzi_norm(hanzi) if hanzi else None, pos=pos, infl_class=infl, register=lex_reg,
                              level=None, score=0, source="kaikki", source_id=f"{word}#{pos_raw}#{etym}",
                              extra={"pos_raw": pos_raw, "etymology": e.get("etymology_text"), "sounds": e.get("sounds")})
                sense_ids = [f"{lex_id}#{i}" for i in range(1, len(senses) + 1)]
                self.sense_rows(lex_id, e, 1)
                self.index.add(lex_id, word, pos, [word] + ([hanzi] if hanzi else []), [reading] if reading else [], len(senses))
                self.sink.add("form", key=search_key(word, lang), surface=word, lang=lang, lexeme_id=lex_id, kind="lemma",
                              features=None, via=None, source="kaikki")
                if reading and reading != word:
                    self.sink.add("form", key=search_key(reading, lang), surface=reading, lang=lang, lexeme_id=lex_id,
                                  kind="reading", features=None, via=None, source="kaikki")
                self.add_forms(lex_id, e, True)
                self.collect_relations(lex_id, e, sense_ids)
            self.entry_lexeme[(word, pos_raw, etym)] = lex_id

    # --- 지연 해소 ---
    def finish(self):
        lang = self.lang
        ok = miss = 0
        for src, word, typ in self.pending_rel:
            lex = src.split("#")[0]
            tgt = self.index.resolve(word, pos=self.index.pos.get(lex))
            if tgt and tgt != lex:
                conf = 0.85 if typ in ("honorific_of", "humble_of", "polite_of") else 0.8
                method = "definition" if typ in ("honorific_of", "humble_of", "polite_of") else "source"
                self.sink.add("relation", src=src, dst=tgt, type=typ, method=method, confidence=conf, sources=["kaikki"])
                ok += 1
            else:
                miss += 1
        self.inc("rel_ok", ok)
        self.inc("rel_unresolved", miss)
        fok = fmiss = 0
        for surface, base, tags, gloss, kind, pos in self.pending_forms:
            tgt = self.index.resolve(base, pos=None)
            if not tgt:
                fmiss += 1
                continue
            key = search_key(surface, lang)
            if not key:
                continue
            if kind == "hanzi" and lang == "ko":
                feats = {"tags": tags}
            else:
                feats = features_from_tags(tags, gloss)
            if kind == "inflection" and "honorific" in feats.get("tags", []):
                kind = "honorific_inflection"
            self.sink.add("form", key=key, surface=surface, lang=lang, lexeme_id=tgt, kind=kind, features=feats, via=None,
                          source="kaikki")
            fok += 1
        self.inc("form_of_ok", fok)
        self.inc("form_of_unresolved", fmiss)
