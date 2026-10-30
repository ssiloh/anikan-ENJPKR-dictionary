"""전체 빌드: python -m anikan.build [--out out/anikan.sqlite]"""
import argparse
import json
import time

from anikan.common import OUT, WORK
from anikan.db import Sink
from anikan.lexindex import LangIndex
from anikan import export
from anikan.inflect import generate
from anikan.link import gloss, hanzi, honorific, honorific_forms, project
from anikan.normalize import english, jmdict, kaikki, kaikki_en, krdict


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT / "anikan.sqlite"))
    args = ap.parse_args(argv)
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    stats = {}
    sink = Sink(args.out)
    ja_index, ko_index = LangIndex("ja"), LangIndex("ko")
    en = english.EnIndex()

    def log(step):
        print(f"[{round(time.time() - t0):4d}s] {step}", flush=True)

    pending = jmdict.run(sink, ja_index, stats)
    jmdict.resolve_relations(sink, ja_index, pending, stats)
    log("jmdict")
    kja = kaikki.Normalizer(sink, "ja", ja_index, stats=stats)
    kja.run(WORK / "kaikki.ja.jsonl")
    kja.finish()
    log("kaikki ja")
    english.run_wordnet(sink, en, stats)
    english.run_ejdict(sink, en, ja_index, stats)
    log("wordnet + ejdict")
    pend_hon, _ = krdict.run(sink, ko_index, ja_index, en, stats)
    krdict.resolve_definition_honorifics(sink, ko_index, pend_hon, stats)
    log("krdict")
    kko = kaikki.Normalizer(sink, "ko", ko_index, stats=stats)
    kko.run(WORK / "kaikki.ko.jsonl")
    kko.finish()
    log("kaikki ko")
    kaikki_en.run(sink, en, ja_index, ko_index, stats)
    log("kaikki en")

    sink.make_indexes()
    gloss.jmdict_gloss(sink, en.lexemes, stats)
    log("jmdict_gloss")
    honorific.curated(sink, {"ja": ja_index, "ko": ko_index}, stats)
    honorific.by_gloss(sink, stats)
    log("honorific")
    hanzi.hanzi_match(sink, stats)
    log("hanzi_match")
    gloss.en_pivot(sink, stats)
    log("en_pivot")
    gloss.wn_concept(sink, en, stats)
    log("wn_concept")
    project.project_antonyms(sink, stats)
    log("antonym projection")

    generate.run_ko(sink, stats)
    generate.run_ja(sink, stats)
    generate.run_ko_romaja(sink, stats)
    log("inflection generators")
    honorific_forms.run(sink, stats)
    export.finalize_db(sink.db, stats)
    log("form index finalized")
    sink.flush()
    export.write_pairs(sink.db, OUT, stats)
    export.write_forms(sink.db, OUT, stats)
    export.write_stats_md(sink.db, stats, OUT / "stats.md")
    log("export")
    (OUT / "build_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    sink.finish()
    print(json.dumps(sink.counts), round(time.time() - t0), "s")


if __name__ == "__main__":
    main()
