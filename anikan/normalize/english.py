"""영어 쪽: WordNet(concept·sense·반의어) + EJDict-hand(뜻·일본어 대역어). 영어 표제어 ID는 `en:{소문자 lemma}`."""
import re
from collections import defaultdict

from anikan.common import WORK, read_jsonl, search_key
from anikan.normalize.maps import map_pos, register_map, region_map
from anikan.parse.wn_lexnames import LEXNAMES

SS_NUM = {"n": 1, "v": 2, "a": 3, "r": 4, "s": 5}


class EnIndex:
    def __init__(self):
        self.lexemes = {}                          # id → lemma(표시용)
        self.synsets_by_lemma = defaultdict(list)  # (lemma, pos) → [synset id] 빈도순
        self.concept_words = {}                    # synset id → [lemma]
        self.concept_gloss = {}
        self.sense_ids = defaultdict(list)         # lexeme id → [sense id]

    @staticmethod
    def lid(lemma):
        return "en:" + lemma.lower().replace("_", " ").strip()

    def has(self, lemma):
        return self.lid(lemma) in self.lexemes


def domain_of(lexfile):
    return lexfile.split(".", 1)[1].lower() if "." in lexfile else lexfile


def run_wordnet(sink, en, stats):
    sensekey = {}
    for r in read_jsonl(WORK / "wordnet.sensekey.jsonl"):
        head, _, tail = r["key"].partition("%")
        ss = int(tail.split(":", 1)[0])
        pos = {1: "n", 2: "v", 3: "a", 4: "r", 5: "a"}[ss]
        sensekey[(head.lower(), r["offset"], pos)] = (r["rank"], r["tag_count"])
    first_case = {}
    syn_rows = list(read_jsonl(WORK / "wordnet.synset.jsonl"))
    tag_total = defaultdict(int)
    for ss in syn_rows:
        lemmas = [w[0].replace("_", " ") for w in ss["words"]]
        en.concept_words[ss["id"]] = lemmas
        en.concept_gloss[ss["id"]] = ss["gloss"]
        sink.add("concept", id=ss["id"], pos=ss["pos"], lemmas=lemmas, gloss=ss["gloss"], lexfile=ss["lexfile"])
        off = ss["id"].split(":")[1].split("-")[0]
        for lemma, lexid in ss["words"]:
            lid = EnIndex.lid(lemma)
            first_case.setdefault(lid, lemma.replace("_", " "))
            rank, cnt = sensekey.get((lemma.lower(), off, ss["pos"]), (None, 0))
            tag_total[lid] += cnt
            sid = f"{lid}#wn:{ss['id'].split(':')[1]}"
            en.sense_ids[lid].append(sid)
            sink.add("sense", id=sid, lexeme_id=lid, ord=rank, definition=ss["gloss"], def_lang="en",
                     glosses=None, register=None, labels={"domain": [domain_of(ss["lexfile"])]},
                     examples=None, extra={"concept": ss["id"], "lexid": lexid, "tag_count": cnt, "rank": rank})
            stats["wn_sense"] = stats.get("wn_sense", 0) + 1
    # 표제어: index.* 의 빈도순 synset 목록
    for r in read_jsonl(WORK / "wordnet.index.jsonl"):
        lid = EnIndex.lid(r["lemma"])
        en.synsets_by_lemma[(r["lemma"].lower(), r["pos"])] = r["synsets"]
        en.lexemes.setdefault(lid, first_case.get(lid, r["lemma"]))
    wn_pos = {}
    for r in syn_rows:
        for lemma, _ in r["words"]:
            wn_pos.setdefault(EnIndex.lid(lemma), r["pos"])
    for lid, lemma in en.lexemes.items():
        sink.add("lexeme", id=lid, lang="en", lemma=lemma, reading=None, hanzi=None, hanzi_norm=None,
                 pos=map_pos("wordnet", wn_pos.get(lid, "n")), infl_class=None, register=None,
                 level={"wn_tagged": tag_total[lid]} if tag_total[lid] else None,
                 score=min(60, 20 + 5 * tag_total[lid].bit_length()) if tag_total[lid] else 0,
                 source="wordnet", source_id=lemma, extra=None)
        sink.add("form", key=search_key(lemma), surface=lemma, lang="en", lexeme_id=lid, kind="lemma", features=None,
                 via=None, source="wordnet")
    # 반의어(어휘 포인터 '!'): ptr = [sym, 대상 offset, 대상 pos, 'ssww']
    ok = 0
    by_id = {r["id"]: r for r in syn_rows}
    for ss in syn_rows:
        for sym, off, ppos, st in ss["ptrs"]:
            if sym != "!" or st == "0000":
                continue
            s_i, t_i = int(st[:2], 16) - 1, int(st[2:], 16) - 1
            tgt = by_id.get(f"wn30:{off}-{ppos}")
            if not tgt or s_i >= len(ss["words"]) or t_i >= len(tgt["words"]):
                continue
            src = f"{EnIndex.lid(ss['words'][s_i][0])}#wn:{ss['id'].split(':')[1]}"
            dst = f"{EnIndex.lid(tgt['words'][t_i][0])}#wn:{tgt['id'].split(':')[1]}"
            sink.add("relation", src=src, dst=dst, type="antonym", method="source", confidence=0.9, sources=["wordnet"])
            ok += 1
    stats["wn_antonym_rel"] = ok
    # 상위어(@)·하위어는 concept 사이 관계라 내보내기에서 쓰지 않는다(후속 확장).
    return syn_rows


CORE = re.compile(r"『([^』]+)』")
PAREN = re.compile(r"[（(][^）)]*[）)]|\[[^\]]*\]|〈[^〉]*〉|《[^》]*》|〔[^〕]*〕")
LEAD = re.compile(r"^[…・~〜～]+(を|に|が|の|と|へ|で)?")
SPLIT = re.compile(r"[,、;；]")


def ejdict_candidates(item):
    """한 뜻 항목에서 일본어 대역어 후보 → [(단어, core 여부)]."""
    core = [c.strip() for c in CORE.findall(item)]
    out = []
    for c in core:
        c = LEAD.sub("", PAREN.sub("", c)).strip()
        if c and not c.isascii():
            out.append((c, True))
    if out:
        return out
    body = PAREN.sub("", item)
    for tok in SPLIT.split(body)[:2]:
        tok = LEAD.sub("", tok).strip(" ・…")
        if tok and not tok.isascii() and len(tok) <= 12:
            out.append((tok, False))
    return out[:1]


def run_ejdict(sink, en, ja_index, stats):
    rm = register_map()
    regm = region_map()
    n_line = 0
    linked = unresolved = 0
    for r in read_jsonl(WORK / "ejdict.jsonl"):
        n_line += 1
        lvl = {"ejdict_lists": r["lists"]} if r["lists"] else None
        score = 95 if "100" in r["lists"] else 85 if "850" in r["lists"] else 70 if "2000" in r["lists"] else 0
        for h in r["heads"]:
            lid = EnIndex.lid(h)
            if lid not in en.lexemes:
                en.lexemes[lid] = h
                sink.add("lexeme", id=lid, lang="en", lemma=h, reading=None, hanzi=None, hanzi_norm=None, pos=None,
                         infl_class=None, register=None, level=lvl, score=score, source="ejdict", source_id=h, extra=None)
                sink.add("form", key=search_key(h), surface=h, lang="en", lexeme_id=lid, kind="lemma", features=None,
                         via=None, source="ejdict")
            else:
                sink.add("form", key=search_key(h), surface=h, lang="en", lexeme_id=lid, kind="variant", features=None,
                         via=None, source="ejdict")
            for k, item in enumerate(r["senses"], 1):
                marks = re.findall(r"《([^》]+)》", item)
                reg = None
                labels = {}
                usage = []
                for m in marks:
                    if ("ejdict", m) in rm and reg is None:
                        reg = rm[("ejdict", m)]
                    elif ("ejdict", m) in regm:
                        labels.setdefault("region", []).append(regm[("ejdict", m)])
                    else:
                        usage.append(m)
                if "〈C〉" in item:
                    usage.append("countable")
                if "〈U〉" in item:
                    usage.append("uncountable")
                if "複数形で" in marks:
                    usage.append("plural-only")
                if usage:
                    labels["usage"] = usage
                sid = f"{lid}#ej:{n_line}.{k}"
                cands = ejdict_candidates(item)
                en.sense_ids[lid].append(sid)
                sink.add("sense", id=sid, lexeme_id=lid, ord=k, definition=item, def_lang="ja",
                         glosses={"ja": [c for c, _ in cands]}, register=reg, labels=labels or None, examples=None,
                         extra={"line": n_line})
                for word, is_core in cands:
                    tgt = ja_index.resolve(word)
                    if tgt:
                        sink.add("link", src=sid, dst=tgt, kind="translation", method="ejdict",
                                 confidence=0.8 if is_core else 0.65, evidence=word, sources=["ejdict", "jmdict"])
                        linked += 1
                    else:
                        unresolved += 1
    stats["ej_link"] = linked
    stats["ej_unresolved"] = unresolved
