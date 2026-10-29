"""영어 kaikki(일·한 번역이 달린 항목) → 영어 표제어·뜻, kaikki_translation / kaikki_triangle 연결."""
from anikan.common import RAW, nfc, read_jsonl, search_key
from anikan.normalize.english import EnIndex
from anikan.normalize.maps import map_pos

POS_HINT = {"noun": "noun", "verb": "verb", "adj": "adj", "adv": "adv", "name": "name"}


def run(sink, en, ja_index, ko_index, stats):
    n_lex = n_tr = n_tri = unl = 0
    seen_pairs = set()
    for e in read_jsonl(RAW / "kaikki/en.filtered.jsonl"):
        word = nfc(e["word"])
        lid = EnIndex.lid(word)
        pos_raw = e.get("pos") or "unk"
        pos = map_pos("kaikki", pos_raw)
        etym = e.get("etymology_number") or 0
        if lid not in en.lexemes:
            en.lexemes[lid] = word
            sink.add("lexeme", id=lid, lang="en", lemma=word, reading=None, hanzi=None, hanzi_norm=None, pos=pos,
                     infl_class=None, register=None, level=None, score=0, source="kaikki", source_id=word, extra=None)
            sink.add("form", key=search_key(word), surface=word, lang="en", lexeme_id=lid, kind="lemma", features=None,
                     via=None, source="kaikki")
            n_lex += 1
        groups = [(k, s) for k, s in enumerate(e["senses"], 1)]
        # 뜻 밖에 달린 번역은 번역표의 뜻 설명(`sense`)별로 묶는다
        by_label = {}
        for t in e.get("translations", []):
            by_label.setdefault(t.get("sense") or "", []).append(t)
        for j, (label, trs) in enumerate(by_label.items(), 1):
            groups.append((1000 + j, {"glosses": [label] if label else [], "tags": [], "translations": trs}))
        for k, s in groups:
            sid = f"{lid}#kk:{pos_raw}:{etym}.{k}"
            gl = [nfc(g) for g in s.get("glosses", [])]
            tr = s["translations"]
            ja_words = [(nfc(t["word"]), t.get("roman")) for t in tr if t.get("lang_code") == "ja" and t.get("word")]
            ko_words = [(nfc(t["word"]), t.get("roman")) for t in tr if t.get("lang_code") == "ko" and t.get("word")]
            sink.add("sense", id=sid, lexeme_id=lid, ord=k, definition="; ".join(gl) or None, def_lang="en",
                     glosses={"ja": [w for w, _ in ja_words], "ko": [w for w, _ in ko_words]}, register=None,
                     labels={"usage": s["tags"]} if s.get("tags") else None, examples=None, extra={"pos": pos_raw})
            ja_ids, ko_ids = [], []
            for w, roman in ja_words:
                tgt = ja_index.resolve(w, pos=pos, roman=roman)
                if tgt:
                    ja_ids.append(tgt)
                else:
                    tgt = "ja:unlinked:" + w
                    unl += 1
                sink.add("link", src=sid, dst=tgt, kind="translation", method="kaikki_translation",
                         confidence=0.8 if not tgt.startswith("ja:unlinked") else 0.5, evidence=w,
                         sources=["kaikki"] + (["jmdict"] if not tgt.startswith("ja:unlinked") else []))
                n_tr += 1
            for w, roman in ko_words:
                tgt = ko_index.resolve(w, pos=pos)
                if tgt:
                    ko_ids.append(tgt)
                else:
                    tgt = "ko:unlinked:" + w
                    unl += 1
                sink.add("link", src=sid, dst=tgt, kind="translation", method="kaikki_translation",
                         confidence=0.8 if not tgt.startswith("ko:unlinked") else 0.5, evidence=w, sources=["kaikki"])
                n_tr += 1
            # 삼각 연결: 같은 영어 뜻에 함께 달린 일·한 단어
            ja_ids, ko_ids = list(dict.fromkeys(ja_ids)), list(dict.fromkeys(ko_ids))
            wide = len(ja_ids) > 3 or len(ko_ids) > 3
            for j in ja_ids:
                for ko in ko_ids:
                    if (j, ko) in seen_pairs:
                        continue
                    seen_pairs.add((j, ko))
                    sink.add("link", src=j, dst=ko, kind="translation", method="kaikki_triangle",
                             confidence=0.6 if wide else 0.75, evidence=sid, sources=["kaikki"])
                    n_tri += 1
    stats["kk_en_lexeme_new"] = n_lex
    stats["kk_en_translation_links"] = n_tr
    stats["kk_triangle_links"] = n_tri
    stats["kk_unlinked"] = unl
