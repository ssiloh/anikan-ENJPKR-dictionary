"""참조 검색 구현(§6.3): python -m anikan.search 드세요 [--db out/anikan.sqlite]"""
import argparse
import json
import sqlite3

from anikan.search.core import search


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--db", default="out/anikan.sqlite")
    ap.add_argument("--lang", default=None)
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    db = sqlite3.connect(a.db)
    res = search(db, a.query, lang=a.lang, limit=a.limit)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return
    for r in res:
        print(f"{r['lemma']} [{r['lang']}/{r['pos']}] ← {r['matched']['surface']} ({r['matched']['kind']})")
        for step in r["explain"]:
            print("   ", step)
        for b in r["base"]:
            print(f"    기본형 → {b['lemma']} ({b['relation']})")
        for t in r["translations"]:
            print(f"    {t['lang']}: {t['lemma']} {t['reading'] or ''} [{t['confidence']}]")


if __name__ == "__main__":
    main()
