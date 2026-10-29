"""한국어기초사전(LMF JSON, XML 변환 꼴) → 중간 JSONL.
원본은 항목이 하나면 dict, 여럿이면 list로 나오는 꼴이라 L()로 맞춘다. 같은 att가 여러 번 나오면 list로 모은다."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

from anikan.common import RAW, WORK, JsonlWriter, nfc


def L(x):
    return x if isinstance(x, list) else ([] if x is None else [x])


def fm(feats):
    """[{att, val}, ...] → {att: val | [val…]}"""
    out = {}
    for f in L(feats):
        a, v = f["att"], f.get("val", "")
        if a in out:
            out[a] = L(out[a]) + [v]
        else:
            out[a] = v
    return out


def parse_sense(s):
    f = fm(s.get("feat"))
    equiv = {}
    for q in L(s.get("Equivalent")):
        e = fm(q["feat"])
        equiv.setdefault(e.get("language"), []).append({"lemma": nfc(e.get("lemma", "")), "definition": nfc(e.get("definition", ""))})
    examples = []
    for x in L(s.get("SenseExample")):
        e = fm(x["feat"])
        examples.append({"type": e.get("type"), "text": [nfc(t) for t in L(e.get("example"))]})
    rels = []
    for r in L(s.get("SenseRelation")):
        e = fm(r["feat"])
        rels.append({"type": e.get("type"), "id": e.get("id"), "lemma": nfc(e.get("lemma", "")), "hom": e.get("homonymNumber")})
    mm = [fm(m["feat"]) for m in L(s.get("Multimedia"))]
    return {"n": int(s["val"]) if str(s.get("val", "")).isdigit() else None, "definition": nfc(f.get("definition", "")),
            "pattern": f.get("syntacticPattern"), "annotation": f.get("annotation"), "equiv": equiv,
            "examples": examples, "relations": rels, "multimedia": mm or None}


def parse_entry(e):
    f = fm(e.get("feat"))
    lemma = {}
    for lm in L(e.get("Lemma")):
        lemma.update(fm(lm["feat"]))
    variants = [nfc(v).strip() for v in re.split(r"\s*,\s*", lemma.get("variant", "")) if v.strip()]
    wf = []
    for w in L(e.get("WordForm")):
        x = fm(w["feat"])
        wf.append({"type": x.get("type"), "form": [nfc(t) for t in L(x.get("form") or x.get("writtenForm"))],
                   "pron": [nfc(t) for t in L(x.get("pronunciation"))], "sound": L(x.get("sound")) or None})
    rf = []
    for r in L(e.get("RelatedForm")):
        x = fm(r["feat"])
        rf.append({"type": x.get("type"), "id": x.get("id"), "form": nfc(x.get("writtenForm", ""))})
    return {"id": e["val"], "lemma": nfc(lemma.get("writtenForm", "")), "variants": variants, "homonym": f.get("homonym_number"),
            "unit": f.get("lexicalUnit"), "pos": f.get("partOfSpeech"), "level": f.get("vocabularyLevel"),
            "origin": f.get("origin"), "semcat": f.get("semanticCategory"), "subcat": f.get("subjectCategiory"),
            "annotation": f.get("annotation"), "wordforms": wf, "related": rf,
            "senses": [parse_sense(s) for s in L(e.get("Sense"))]}


def parse(src_dir=None, out_dir=None):
    src_dir = Path(src_dir or RAW / "krdict/json")
    out_dir = out_dir or WORK
    st = {"entries": 0, "senses": 0, "unit": Counter(), "wf_type": Counter(), "rel_type": Counter(),
          "relform_type": Counter(), "equiv_langs": Counter(), "ja_senses": 0, "en_senses": 0, "origin": 0, "hanja": 0}
    with JsonlWriter(out_dir / "krdict.entry.jsonl") as w:
        for p in sorted(src_dir.glob("*.json"), key=lambda p: int(p.name.split("_")[0])):
            d = json.load(open(p, encoding="utf-8"))
            for e in L(d["LexicalResource"]["Lexicon"]["LexicalEntry"]):
                t = parse_entry(e)
                w.write(t)
                st["entries"] += 1
                st["unit"][t["unit"]] += 1
                if t["origin"]:
                    st["origin"] += 1
                    if re.search(r"[一-鿿]", t["origin"]):
                        st["hanja"] += 1
                for x in t["wordforms"]:
                    st["wf_type"][x["type"]] += 1
                for x in t["related"]:
                    st["relform_type"][x["type"]] += 1
                for s in t["senses"]:
                    st["senses"] += 1
                    for r in s["relations"]:
                        st["rel_type"][r["type"]] += 1
                    for lang in s["equiv"]:
                        st["equiv_langs"][lang] += 1
                    if "일본어" in s["equiv"]:
                        st["ja_senses"] += 1
                    if "영어" in s["equiv"]:
                        st["en_senses"] += 1
            del d
            print(p.name, st["entries"], file=sys.stderr, flush=True)
    return st


if __name__ == "__main__":
    st = parse()
    for k, v in st.items():
        print(k, dict(v) if isinstance(v, Counter) else v)
