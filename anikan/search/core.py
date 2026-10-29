"""검색: 표제어 > 표기 변형·읽기 > 활용형 > 경어 활용형 순으로 form 색인을 찾고,
경어 표제어는 honorific_of / humble_of / polite_of 를 따라 기본형도 함께 내며, 기본형의 link로 다른 두 언어 대역어를 붙인다."""
import json
from collections import defaultdict

from anikan.common import search_key
from anikan.normalize.romaji import romaji_key

KIND_RANK = {"lemma": 0, "variant": 1, "hanzi": 1, "reading": 2, "romaji": 2, "inflection": 3,
             "honorific_inflection": 4, "lexical_honorific": 5}
HON_TYPES = ("honorific_of", "humble_of", "polite_of")
MIN_LINK = 0.5


def rng(lid):
    """표제어의 뜻 ID(`lid#…`) 범위 — LIKE 'lid#%' 는 인덱스를 못 타므로 범위 비교를 쓴다('$'는 '#' 바로 다음 문자)."""
    return lid + "#", lid + "$"


def _keys(q, lang):
    keys = {(search_key(q, "ja"), "ja"), (search_key(q, "ko"), "ko"), (search_key(q), "en"), (romaji_key(q), "ja"),
            (romaji_key(q), "ko")}
    return [(k, l) for k, l in keys if k and (lang is None or l == lang)]


def _explain(kind, features, matched):
    if kind in ("inflection", "honorific_inflection") and features:
        bits = []
        if features.get("honorific"):
            bits.append("높임" if matched["lang"] == "ko" else "尊敬")
        if features.get("humble"):
            bits.append("謙譲")
        if features.get("politeness"):
            bits.append({"polite": "정중", "formal": "격식"}.get(features["politeness"], features["politeness"]))
        if features.get("tense"):
            bits.append(features["tense"])
        if features.get("polarity") == "neg":
            bits.append("부정")
        return f"{matched['surface']} = " + "·".join(bits) if bits else None
    return None


def search(db, query, lang=None, limit=8, with_translations=True):
    keys = _keys(query, lang)
    hits = {}
    for key, l in keys:
        for lid, surface, kind, features, via in db.execute(
                "SELECT lexeme_id, surface, kind, features, via FROM form WHERE key = ? AND lang = ?", (key, l)):
            rank = KIND_RANK.get(kind, 6)
            if lid not in hits or rank < hits[lid][0]:
                hits[lid] = (rank, surface, kind, json.loads(features) if features else None, via, l)
    info = {}
    for lid in hits:
        row = db.execute("SELECT lemma, lang, pos, reading, register, score FROM lexeme WHERE id = ?", (lid,)).fetchone()
        if row:
            info[lid] = row
    order = sorted(hits, key=lambda i: (hits[i][0], -(info[i][5] or 0)) if i in info else (99, 0))
    results = []
    for lid in order[:limit]:
        if lid not in info:
            continue
        rank, surface, kind, feat, via, l = hits[lid]
        lemma, lg, pos, reading, reg, score = info[lid]
        matched = {"surface": surface, "kind": kind, "features": feat, "lang": lg}
        explain = []
        e = _explain(kind, feat, matched)
        if e:
            explain.append(e)
        if via:
            vl = db.execute("SELECT lemma FROM lexeme WHERE id = ?", (via,)).fetchone()
            explain.append(f"{surface}: 경어 표제어 {vl[0] if vl else via}")
        base = []
        for dst, typ, conf in db.execute(
                f"SELECT r.dst, r.type, MAX(r.confidence) FROM relation r WHERE r.type IN {HON_TYPES} AND "
                f"(r.src = ? OR (r.src >= ? AND r.src < ?)) GROUP BY r.dst, r.type ORDER BY 3 DESC", (lid, *rng(lid))):
            b = db.execute("SELECT id, lemma FROM lexeme WHERE id = ?", (dst.split("#")[0],)).fetchone()
            if b:
                base.append({"id": b[0], "lemma": b[1], "relation": typ, "confidence": conf})
        # 반대 방향: 이 표제어의 경어 대응
        honorifics = []
        for src, typ, conf in db.execute(
                f"SELECT r.src, r.type, MAX(r.confidence) FROM relation r WHERE r.type IN {HON_TYPES} AND "
                f"(r.dst = ? OR (r.dst >= ? AND r.dst < ?)) GROUP BY r.src, r.type ORDER BY 3 DESC", (lid, *rng(lid))):
            b = db.execute("SELECT id, lemma FROM lexeme WHERE id = ?", (src.split("#")[0],)).fetchone()
            if b:
                honorifics.append({"id": b[0], "lemma": b[1], "relation": typ, "confidence": conf})
        res = {"id": lid, "lemma": lemma, "lang": lg, "pos": pos, "reading": reading, "register": reg, "matched": matched,
               "explain": explain, "base": base, "honorific_counterparts": honorifics, "translations": []}
        if with_translations:
            res["translations"] = translations(db, [lid] + [b["id"] for b in base])
        results.append(res)
    return results


def translations(db, lex_ids, limit=12):
    """표제어(들)의 뜻에서 나가는 연결과 표제어끼리의 연결을 noisy-OR로 합쳐 다른 언어 표제어를 낸다."""
    acc = defaultdict(dict)       # 대상 → {방법: 최대 신뢰도} — 같은 방법의 여러 뜻은 합치지 않고 최댓값만
    for lid in lex_ids:
        rows = db.execute("SELECT dst, method, confidence FROM link WHERE kind = 'translation' AND (src = ? OR (src >= ? AND src < ?))",
                          (lid, *rng(lid))).fetchall()
        # 반대 방향: 이 표제어(또는 그 뜻)를 dst로 삼는 다른 언어 쪽 연결
        for src, m, c in db.execute("SELECT src, method, confidence FROM link WHERE kind = 'translation' AND "
                                    "(dst = ? OR (dst >= ? AND dst < ?))", (lid, *rng(lid))):
            rows.append((src.split("#")[0], m, c))
        for dst, method, conf in rows:
            a = acc[dst.split("#")[0]]
            a[method] = max(conf, a.get(method, 0))
    out = []
    for dst, by_method in acc.items():
        rest = 1.0
        for c in by_method.values():
            rest *= 1 - c
        conf, methods = 1 - rest, by_method.keys()
        if conf < MIN_LINK or dst.startswith(("ja:unlinked", "ko:unlinked")):
            continue
        row = db.execute("SELECT lemma, lang, reading FROM lexeme WHERE id = ?", (dst,)).fetchone()
        if row and row[1] != dst.split(":")[0]:
            continue
        if row:
            out.append({"id": dst, "lemma": row[0], "lang": row[1], "reading": row[2], "confidence": round(conf, 2),
                        "methods": sorted(methods)})
    out.sort(key=lambda r: -r["confidence"])
    return out[:limit]
