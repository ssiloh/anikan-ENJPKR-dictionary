"""한국어기초사전 중간 JSONL → lexeme · sense · form · relation · link(krdict_equivalent)."""
import re

from anikan.common import WORK, hanzi_norm, is_placeholder, read_jsonl, search_key
from anikan.normalize.english import EnIndex
from anikan.normalize.maps import map_pos, pick_register, register_map

UNIT_POS = {"구": "phrase", "속담": "proverb", "관용구": "idiom", "문법‧표현": "grammar", "문법·표현": "grammar"}
UNIT_SHORT = {"구": "p", "속담": "s", "관용구": "i", "문법‧표현": "g", "문법·표현": "g"}
LEVEL = {"초급": 1, "중급": 2, "고급": 3}
LEVEL_SCORE = {"초급": 90, "중급": 60, "고급": 30}
# 관계 유형: (유형, 방향) — 방향 'fwd'면 src(이 표제어)→dst(대상), 'rev'면 대상→이 표제어
REL = {
    "반대말": ("antonym", "fwd"), "유의어": ("synonym", "fwd"), "참고어": ("see_also", "fwd"),
    "큰말": ("large_form", "fwd"), "작은말": ("small_form", "fwd"), "센말": ("strong_form", "fwd"),
    "여린말": ("soft_form", "fwd"),
    "준말": ("abbrev_of", "rev"),     # A의 준말 B → B는 A의 준말
    "본말": ("abbrev_of", "fwd"),     # A의 본말 B → A는 B의 준말
    "높임말": ("honorific_of", "rev"),  # A의 높임말 B → B는 A의 높임말
    "낮춤말": ("humble_of", "rev"),
}
DEF_HON = re.compile(r"^\((높임말로|높이는 말로|조금 높이는 말로|낮추는 말로|낮춤말로)\)\s*(.+?)\.?\s*$")
DEF_HON_TYPE = {"높임말로": "honorific_of", "높이는 말로": "honorific_of", "조금 높이는 말로": "honorific_of",
                "낮추는 말로": "humble_of", "낮춤말로": "humble_of"}
JA_ITEM = re.compile(r"^(?P<read>[^【]*?)(?:【(?P<kanji>[^】]+)】)?\s*$")
EN_LEAD = re.compile(r"^(to |be |a |an |the )")


def parse_ja_equiv(lemma):
    """`はし【端】。ふち【縁】` → [(읽기, 한자 또는 None)]"""
    out = []
    for item in re.split(r"[。]", lemma):
        item = item.strip()
        if not item or is_placeholder(item) or "対訳語" in item:
            continue
        m = JA_ITEM.match(item)
        if not m:
            out.append((item, None))
            continue
        read, kanji = (m.group("read") or "").strip(), m.group("kanji")
        out.append((read or kanji, kanji))
    return out


def clean_en(term):
    t = re.sub(r"\([^)]*\)", "", term).strip().lower()
    return t, EN_LEAD.sub("", t)


def clean_lemma(s):
    return s.replace("^", " ").strip()


def run(sink, ko_index, ja_index, en, stats):
    rm = register_map()
    pending_hon = []   # (sense_id, 대상 표제어, type)
    ent_ids = set()
    n_ja = n_ja_unl = n_en = 0
    pos_of = {}
    nonword = {}   # 관용구·속담·구·문법은 표제어(단어)의 target_code를 공유하므로 순번을 붙인다
    for e in read_jsonl(WORK / "krdict.entry.jsonl"):
        if e["unit"] == "단어":
            lex_id = f"ko:krdict:{e['id']}"
        else:
            nonword[e["id"]] = nonword.get(e["id"], 0) + 1
            lex_id = f"ko:krdict:{e['id']}:{UNIT_SHORT.get(e['unit'], 'x')}{nonword[e['id']]}"
        ent_ids.add(e["id"])
        lemma = clean_lemma(e["lemma"])
        unit = e["unit"]
        pos = UNIT_POS.get(unit) or map_pos("krdict", e["pos"] or "품사 없음") or None
        pos_of[lex_id] = pos
        origin = e["origin"]
        hanzi = origin if origin and re.search(r"[一-鿿]", origin) else None
        pron = next((w["pron"][0] for w in e["wordforms"] if w["type"] == "발음" and w["pron"]), None)
        sense_regs = []
        for s in e["senses"]:
            m = DEF_HON.match(s["definition"])
            sense_regs.append(rm.get(("krdict", f"({m.group(1)})")) if m else None)
        keigo = [r for r in sense_regs if r in ("honorific", "humble")]
        lex_reg = keigo[0] if keigo else (sense_regs[0] if sense_regs and all(r == sense_regs[0] for r in sense_regs) else None)
        lv = LEVEL.get(e["level"])
        sink.add("lexeme", id=lex_id, lang="ko", lemma=lemma, reading=pron, hanzi=hanzi,
                 hanzi_norm=hanzi_norm(hanzi) if hanzi else None, pos=pos, infl_class=None, register=lex_reg,
                 level={"krdict": e["level"], "n": lv} if lv else None, score=LEVEL_SCORE.get(e["level"], 0),
                 source="krdict", source_id=e["id"],
                 extra={"homonym": e["homonym"], "unit": unit, "pos_raw": e["pos"], "origin": origin,
                        "semcat": e["semcat"], "subcat": e["subcat"], "annotation": e["annotation"],
                        "wordforms": e["wordforms"], "related": e["related"], "variants": e["variants"]})
        surfaces = [lemma] + ([hanzi] if hanzi else [])
        ko_index.add(lex_id, lemma, pos, surfaces, (), len(e["senses"]), LEVEL_SCORE.get(e["level"], 0) + (0 if unit == "단어" else -50))

        seen = set()

        def form(surface, kind, features=None):
            key = search_key(surface, "ko")
            if key and (key, kind) not in seen:
                seen.add((key, kind))
                sink.add("form", key=key, surface=surface, lang="ko", lexeme_id=lex_id, kind=kind, features=features,
                         via=None, source="krdict")

        form(lemma, "lemma")
        if hanzi:
            form(hanzi, "hanzi")
        stem = lemma.endswith("-")
        for v in e["variants"]:
            form(clean_lemma(v), "inflection" if stem else "variant")
        for w in e["wordforms"]:
            if w["type"] == "발음":
                for p in w["pron"]:
                    form(p, "reading")
            elif w["type"] == "활용":
                for f in w["form"] + w["pron"]:
                    form(f, "inflection", {"source": "krdict"})
        for r in e["related"]:
            if r["type"] == "파생어" and r["form"]:
                pass  # 파생어는 자체 표제어가 있으므로 관계로만 둔다(아래)

        for s in e["senses"]:
            n = s["n"] or 1
            sid = f"{lex_id}#{n}"
            reg = sense_regs[e["senses"].index(s)]
            labels = {}
            if e["semcat"]:
                labels["domain"] = [e["semcat"]]
            if e["subcat"]:
                labels["subject"] = [e["subcat"]]
            if s["pattern"]:
                labels["pattern"] = s["pattern"]
            ex = []
            for x in s["examples"]:
                ex.append({"text": " ".join(x["text"]), "translation": None, "lang": "ko", "source": "krdict", "type": x["type"]})
            ja_items = [it for q in s["equiv"].get("일본어", []) for it in parse_ja_equiv(q["lemma"])]
            en_items = [t.strip() for q in s["equiv"].get("영어", []) for t in re.split(r"[;]", q["lemma"])
                        if t.strip() and not is_placeholder(t)]
            glosses = {"ja": [f"{r}【{k}】" if k else r for r, k in ja_items], "en": en_items}
            ja_def = next((q["definition"] for q in s["equiv"].get("일본어", []) if q["definition"]), None)
            en_def = next((q["definition"] for q in s["equiv"].get("영어", []) if q["definition"]), None)
            sink.add("sense", id=sid, lexeme_id=lex_id, ord=n, definition=s["definition"], def_lang="ko", glosses=glosses,
                     register=reg, labels=labels or None, examples=ex or None,
                     extra={"definition_ja": ja_def, "definition_en": en_def, "annotation": s["annotation"],
                            "multimedia": s["multimedia"]})
            stats["kr_sense"] = stats.get("kr_sense", 0) + 1
            # 대역어 → 일본어
            for read, kanji in ja_items:
                tgt = ja_index.resolve(kanji or read, reading=read, pos=pos)
                if not tgt and kanji:
                    tgt = ja_index.resolve(read)
                if tgt:
                    sink.add("link", src=sid, dst=tgt, kind="translation", method="krdict_equivalent", confidence=0.9,
                             evidence=f"{read}【{kanji}】" if kanji else read, sources=["krdict", "jmdict"])
                    n_ja += 1
                else:
                    sink.add("link", src=sid, dst="ja:unlinked:" + (kanji or read), kind="translation",
                             method="krdict_equivalent", confidence=0.6, evidence=f"{read}【{kanji}】" if kanji else read,
                             sources=["krdict"])
                    n_ja_unl += 1
            # 대역어 → 영어
            for term in en_items:
                full, short = clean_en(term)
                lid = next((x for x in (EnIndex.lid(full), EnIndex.lid(short)) if x in en.lexemes), None)
                if lid:
                    sink.add("link", src=sid, dst=lid, kind="translation", method="krdict_equivalent", confidence=0.9,
                             evidence=term, sources=["krdict"])
                    n_en += 1
            # 뜻 관계
            for r in s["relations"]:
                if r["type"] not in REL or not r["id"]:
                    continue
                typ, direction = REL[r["type"]]
                dst = f"ko:krdict:{r['id']}"
                a, b = (sid, dst) if direction == "fwd" else (dst, lex_id)
                sink.add("relation", src=a, dst=b, type=typ, method="source", confidence=0.95, sources=["krdict"])
                stats["kr_rel_" + r["type"]] = stats.get("kr_rel_" + r["type"], 0) + 1
            m = DEF_HON.match(s["definition"])
            if m:
                pending_hon.append((sid, m.group(2), DEF_HON_TYPE[m.group(1)], pos))
        for r in e["related"]:
            if r["id"] and r["type"] in ("파생어", "☞(가 보라)"):
                typ = "derived" if r["type"] == "파생어" else "see_also"
                sink.add("relation", src=lex_id, dst=f"ko:krdict:{r['id']}", type=typ, method="source", confidence=0.95,
                         sources=["krdict"])
    stats["kr_ja_links"], stats["kr_ja_unlinked"], stats["kr_en_links"] = n_ja, n_ja_unl, n_en
    return pending_hon, ent_ids


def resolve_definition_honorifics(sink, ko_index, pending, stats):
    """뜻풀이 「(높임말로) X.」에서 X가 표제어 하나이면 기본형 관계로 (§6.1)."""
    ok = multi = miss = 0
    for sid, word, typ, pos in pending:
        word = word.strip()
        if " " in word or not word:
            multi += 1       # 풀어쓴 설명은 대역어 일치로 따로 처리(link/honorific.py)
            continue
        tgt = ko_index.resolve(word, pos=pos)
        lex = sid.split("#")[0]
        if tgt and tgt != lex:
            sink.add("relation", src=sid, dst=tgt, type=typ, method="definition", confidence=0.9, sources=["krdict"])
            ok += 1
        else:
            miss += 1
    stats["kr_def_hon_ok"], stats["kr_def_hon_phrase"], stats["kr_def_hon_unresolved"] = ok, multi, miss
