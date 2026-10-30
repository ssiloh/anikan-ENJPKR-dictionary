"""JMdict 중간 JSONL → lexeme · sense · form · 원본 관계(ant/xref)."""
from anikan.common import WORK, hanzi_norm, read_jsonl, search_key
from anikan.normalize.maps import (domain_map, jmdict_level, jmdict_pos, pick_register, region_map, register_map)
from anikan.lexindex import LangIndex
from anikan.normalize.romaji import to_romaji

HONORIFIC_TYPES = {"hon": "honorific_of", "hum": "humble_of", "pol": "polite_of"}


def run(sink, ja_index, stats):
    rm = register_map()
    dm = domain_map()
    regm = region_map()
    pending_rel = []
    for e in read_jsonl(WORK / "jmdict.entry.jsonl"):
        lex_id = f"ja:jmdict:{e['seq']}"
        kebs = [k["keb"] for k in e["k"]]
        rebs = [r["reb"] for r in e["r"]]
        lemma = kebs[0] if kebs else rebs[0]
        reading = None
        for r in e["r"]:
            if not r["restr"] or lemma in r["restr"]:
                reading = r["reb"]
                break
        reading = reading or rebs[0]
        senses = e["s"]
        pos, infl = jmdict_pos(senses[0]["pos"]) if senses else (None, None)
        # 모든 뜻이 같은 문체이면 표제어 문체로
        sense_regs = []
        for s in senses:
            vals = [rm[("jmdict", m)] for m in s["misc"] if ("jmdict", m) in rm]
            sense_regs.append(pick_register(vals))
        keigo = [r for r in sense_regs if r in ("honorific", "humble", "polite")]
        lex_reg = keigo[0] if keigo else (sense_regs[0] if sense_regs and all(r == sense_regs[0] for r in sense_regs) else None)
        pri = [p for k in e["k"] for p in k["pri"]] + [p for r in e["r"] for p in r["pri"]]
        level, score = jmdict_level(pri)
        sink.add("lexeme", id=lex_id, lang="ja", lemma=lemma, reading=reading, hanzi=kebs[0] if kebs else None,
                 hanzi_norm=hanzi_norm(kebs[0]) if kebs else None, pos=pos, infl_class=infl, register=lex_reg,
                 level=level, score=score, source="jmdict", source_id=e["seq"],
                 extra={"k": e["k"], "r": e["r"], "pos_raw": senses[0]["pos"] if senses else []})
        ja_index.add(lex_id, lemma, pos, kebs, [reading] + [r for r in rebs if r != reading], len(senses), score)

        # 표기·읽기·로마자 색인
        seen = set()

        def form(surface, kind, via=None, features=None):
            key = search_key(surface, "ja")
            if key and (key, kind) not in seen:
                seen.add((key, kind))
                sink.add("form", key=key, surface=surface, lang="ja", lexeme_id=lex_id, kind=kind,
                         features=features, via=via, source="jmdict")

        form(lemma, "lemma")
        for k in kebs[1:]:
            form(k, "variant")
        for k in e["k"]:
            if set(k["inf"]) & {"rK", "oK", "iK", "sK"} and k["keb"] != lemma:
                form(k["keb"], "variant", features={"inf": k["inf"]})
        for r in rebs:
            form(r, "reading" if kebs else "lemma")
            rom = to_romaji(r)
            if rom:
                form(rom, "romaji")
        if len(kebs) > 0 and kebs[0] and kebs[0] != hanzi_norm(kebs[0]):
            pass

        for n, s in enumerate(senses, 1):
            sid = f"{lex_id}#{n}"
            labels = {}
            fields = sorted({dm.get(f, f) for f in s["field"]})
            if fields:
                labels["domain"] = fields
            regions = [regm.get(("jmdict", d), "region:" + d) for d in s["dial"]]
            if regions:
                labels["region"] = regions
            usage = [m for m in s["misc"] if ("jmdict", m) not in rm]
            if usage:
                labels["usage"] = usage
            if s["s_inf"]:
                labels["note"] = s["s_inf"]
            if s["stagk"] or s["stagr"]:
                labels["restrict"] = {"keb": s["stagk"], "reb": s["stagr"]}
            ex = [{"text": x["text"], "translation": x["tr"], "lang": "ja", "source": x["src"]} for x in s["example"] if x["text"]]
            glosses = {"en": s["gloss"].get("eng", [])}
            others = {k: v for k, v in s["gloss"].items() if k != "eng"}
            sink.add("sense", id=sid, lexeme_id=lex_id, ord=n, definition=None, def_lang=None, glosses=glosses,
                     register=sense_regs[n - 1], labels=labels or None, examples=ex or None,
                     extra={"pos": s["pos"], "misc": s["misc"], "field": s["field"], "dial": s["dial"],
                            "lsource": s["lsource"], "gloss_other": others or None})
            stats["jm_sense"] = stats.get("jm_sense", 0) + 1
            for a in s["ant"]:
                pending_rel.append((sid, a, "antonym"))
            for x in s["xref"]:
                reg = sense_regs[n - 1]
                t = "see_also"
                if reg in ("honorific", "humble", "polite"):
                    t = {"honorific": "honorific_of", "humble": "humble_of", "polite": "polite_of"}[reg]
                pending_rel.append((sid, x, t))
        stats["jm_lexeme"] = stats.get("jm_lexeme", 0) + 1
    return pending_rel


def resolve_relations(sink, ja_index, pending, stats):
    """「単語・読み・番号」꼴 참조를 표제어(또는 뜻) ID로 푼다."""
    ok = miss = 0
    for src, ref, typ in pending:
        parts = ref.split("・")
        num = None
        if parts and parts[-1].isdigit():
            num = int(parts.pop())
        word = parts[0]
        reading = parts[1] if len(parts) > 1 else None
        tgt = ja_index.resolve(word, reading=reading)
        if not tgt:
            miss += 1
            continue
        if num and num <= ja_index.nsense.get(tgt, 0):
            tgt = f"{tgt}#{num}"
        method = "source"
        sink.add("relation", src=src, dst=tgt, type=typ, method=method, confidence=0.9, sources=["jmdict"])
        ok += 1
    stats["jm_rel_ok"] = ok
    stats["jm_rel_unresolved"] = miss
