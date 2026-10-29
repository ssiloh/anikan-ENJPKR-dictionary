"""kaikki(Wiktionary JSONL) 일본어·한국어 → 줄여 쓴 중간 JSONL. 영어는 fetch 단계에서 이미 거름."""
import sys

from anikan.common import RAW, WORK, JsonlWriter, nfc, read_jsonl

SKIP_FORM_TAGS = {"table-tags", "inflection-template", "class"}


def _words(items):
    return [nfc(x.get("word", "")) for x in items or [] if x.get("word")]


def trim_sense(s):
    d = {"glosses": [nfc(g) for g in s.get("glosses", [])]}
    if s.get("raw_glosses"):
        d["raw"] = [nfc(g) for g in s["raw_glosses"]]
    for k in ("tags", "topics"):
        if s.get(k):
            d[k] = s[k]
    for k in ("synonyms", "antonyms", "related", "derived"):
        w = _words(s.get(k))
        if w:
            d[k] = w
    if s.get("form_of"):
        d["form_of"] = [nfc(x.get("word", "")) for x in s["form_of"]]
    if s.get("alt_of"):
        d["alt_of"] = [nfc(x.get("word", "")) for x in s["alt_of"]]
    ex = [{"text": nfc(e.get("text", "")), "en": nfc(e.get("english") or e.get("translation") or "")}
          for e in s.get("examples", []) if e.get("text")]
    if ex:
        d["examples"] = ex
    tr = [{"lang": t.get("lang_code"), "word": nfc(t.get("word", "")), "roman": t.get("roman")}
          for t in s.get("translations", []) if t.get("word")]
    if tr:
        d["translations"] = tr
    return d


def trim_entry(e):
    forms = []
    for f in e.get("forms", []):
        tags = f.get("tags", [])
        if SKIP_FORM_TAGS & set(tags):
            continue
        forms.append({"form": nfc(f["form"]), "tags": tags, **({"roman": f["roman"]} if f.get("roman") else {})})
    d = {"word": nfc(e["word"]), "pos": e.get("pos"), "forms": forms,
         "senses": [trim_sense(s) for s in e.get("senses", [])]}
    for k in ("etymology_number", "etymology_text", "redirects"):
        if e.get(k):
            d[k] = e[k]
    sounds = []
    for s in e.get("sounds", []):
        for k in ("ipa", "hangeul", "other"):
            if s.get(k):
                sounds.append({k: s[k]})
    if sounds:
        d["sounds"] = sounds
    for k in ("synonyms", "antonyms", "related", "derived"):
        w = _words(e.get(k))
        if w:
            d[k] = w
    return d


def parse(lang, src=None, out_dir=None):
    src = src or RAW / f"kaikki/{lang}.jsonl"
    out_dir = out_dir or WORK
    n = 0
    stats = {"entries": 0, "senses": 0, "soft_redirect": 0, "romanization_entries": 0}
    with JsonlWriter(out_dir / f"kaikki.{lang}.jsonl") as w:
        for e in read_jsonl(src):
            t = trim_entry(e)
            w.write(t)
            stats["entries"] += 1
            stats["senses"] += len(t["senses"])
            if t["pos"] == "soft-redirect":
                stats["soft_redirect"] += 1
    return stats


if __name__ == "__main__":
    for lang in sys.argv[1:] or ["ja", "ko"]:
        print(lang, parse(lang))
