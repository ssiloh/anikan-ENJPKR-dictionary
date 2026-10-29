"""어휘적 경어 색인(§3.1 form.kind='lexical_honorific'): 경어 표제어(召し上がる·드시다)의 표기·활용형을
기본형(食べる·먹다) 줄로도 넣고 `via`에 경어 표제어 id를 남긴다. 기본형이 여럿인 경어는 신뢰도 순으로 모두."""
import json

HON_TYPES = ("honorific_of", "humble_of", "polite_of")
COPY_KINDS = ("lemma", "variant", "reading", "inflection", "honorific_inflection")


def run(sink, stats, min_conf=0.6):
    db = sink.db
    rels = {}
    for src, dst, typ, conf in db.execute(
            f"SELECT src, dst, type, MAX(confidence) FROM relation WHERE type IN {HON_TYPES} AND confidence >= ? GROUP BY src, dst, type",
            (min_conf,)):
        h, p = src.split("#")[0], dst.split("#")[0]
        if h != p:
            k = (h, p)
            if conf > rels.get(k, (None, 0))[1]:
                rels[k] = (typ, conf)
    n = 0
    for (h, p), (typ, conf) in rels.items():
        lang = h.split(":")[0]
        if not p.startswith(lang + ":"):
            continue
        for key, surface, kind, features in db.execute(
                f"SELECT key, surface, kind, features FROM form WHERE lexeme_id = ? AND kind IN {COPY_KINDS}", (h,)):
            feat = json.loads(features) if features else {}
            feat.update({"via_relation": typ, "confidence": conf})
            sink.add("form", key=key, surface=surface, lang=lang, lexeme_id=p, kind="lexical_honorific", features=feat,
                     via=h, source="relation")
            n += 1
    sink.flush()
    stats["lexical_honorific_forms"] = n
    stats["lexical_honorific_pairs"] = len(rels)
