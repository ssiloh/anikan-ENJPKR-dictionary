"""웹 사전용 슬림 데이터(정적 호스팅용 JSON 샤드). python -m anikan.export.slim [--db out/anikan.sqlite] [--out out/site/data]

- `lex/{샤드}.json`: 표제어 상세(뜻·예문·대역어·관계). 대역어·관계는 표시용 이름을 함께 담아 한 번의 요청으로 그린다.
- `idx/{샤드}.json`: 검색 색인. 열쇠(form.key)의 FNV-1a 32비트 해시로 샤딩하므로 정확 일치 조회는 파일 하나만 받는다.
- `manifest.json`: 샤드 수·해시 방식·코드표(품사·경어·활용 자질)·출처 표시.
제외: en_pivot(정밀도 34%), concept·wn_concept, extra 열. 규칙 생성 활용형은 기본 포함(--no-rule-forms로 제외)."""
import argparse
import json
import math
import sqlite3
import time
from collections import defaultdict
from pathlib import Path

from anikan.common import OUT, ROOT, dumps
from anikan.export import combine

EXCLUDE_METHODS = ("en_pivot",)
RULE_SOURCES_HEAVY = ("rule:ko-si", "rule:ja-masu", "rule:ja-keigo")     # 브라우저에서 같은 규칙으로 생성할 수 있는 것
KIND_CODE = {"lemma": 0, "variant": 1, "hanzi": 1, "reading": 2, "romaji": 3, "inflection": 4, "honorific_inflection": 5,
             "lexical_honorific": 6}
KIND_NAMES = ["lemma", "variant", "reading", "romaji", "inflection", "honorific_inflection", "lexical_honorific"]
KIND_RANK = {0: 0, 1: 1, 2: 2, 3: 2, 4: 3, 5: 4, 6: 5}
TARGET_SHARD_BYTES = 120_000
MAX_EXAMPLES = 3
MAX_HITS_PER_KEY = 60
REL_TYPES = {"antonym": "ant", "synonym": "syn", "honorific_of": "hon", "humble_of": "hum", "polite_of": "pol"}


def fnv1a(s):
    """FNV-1a 32비트(UTF-8 바이트). 자바스크립트에서도 같은 값이 나오도록 정수 연산만 쓴다."""
    h = 0x811C9DC5
    for b in s.encode("utf-8"):
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def pow2_at_least(x):
    return 1 << max(0, math.ceil(math.log2(max(1, x))))


def feature_code(features_json):
    """form.features JSON → 짧은 문자열(정렬된 자질 목록). 없으면 ''."""
    if not features_json:
        return ""
    f = json.loads(features_json)
    parts = set(f.get("tags", []))
    for k in ("politeness", "tense", "polarity", "mood", "connective", "modifier", "keigo"):
        if f.get(k):
            parts.add(str(f[k]))
    if f.get("honorific"):
        parts.add("honorific")
    if f.get("humble"):
        parts.add("humble")
    parts -= {"indicative", "canonical", "hangeul"}
    return ",".join(sorted(parts))


def run(db_path, out_dir, with_rule_forms=True, min_conf=0.7, top_per_lang=8, min_rel=0.6, log=print):
    t0 = time.time()
    out_dir = Path(out_dir)
    for d in ("lex", "idx"):
        (out_dir / d).mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    stats = {"min_conf": min_conf, "top_per_lang": top_per_lang, "with_rule_forms": with_rule_forms}

    # --- 표제어 ---
    info = {}
    for lid, lang, lemma, reading, hanzi, pos, reg, level, score, source in db.execute(
            "SELECT id, lang, lemma, reading, hanzi, pos, register, level, score, source FROM lexeme"):
        info[lid] = (lang, lemma, reading, hanzi, pos, reg, json.loads(level) if level else None, score or 0, source)
    log(f"lexemes {len(info):,}")

    # --- 표제어 단위 연결(en_pivot·concept 제외) ---
    methods_ph = ",".join("?" * len(EXCLUDE_METHODS))
    edges = defaultdict(dict)
    for src, dst, method, conf in db.execute(
            f"SELECT src, dst, method, confidence FROM link WHERE kind = 'translation' AND method NOT IN ({methods_ph})", EXCLUDE_METHODS):
        a, b = src.split("#")[0], dst.split("#")[0]
        if a not in info or b not in info or a == b or info[a][0] == info[b][0]:
            continue
        for x, y in ((a, b), (b, a)):
            cur = edges[(x, y)].get(method)
            if not cur or conf > cur[0]:
                edges[(x, y)][method] = (conf, None)
    trans = defaultdict(lambda: defaultdict(list))        # 표제어 → 언어 → [(conf, 대상)]
    for (a, b), m in edges.items():
        c = combine(m)
        if c >= min_conf:
            trans[a][info[b][0]].append((c, b, "+".join(sorted(m))))
    del edges
    # --- 포함할 표제어: ja·ko 전부 + 번역이 있는 en ---
    include = [lid for lid, v in info.items() if v[0] in ("ja", "ko") or lid in trans]
    include.sort(key=lambda i: (info[i][0], info[i][8], i))
    nid = {lid: n for n, lid in enumerate(include, 1)}
    stats["lexemes_included"] = {lang: sum(1 for i in include if info[i][0] == lang) for lang in ("ja", "ko", "en")}
    log(f"included {len(include):,}")

    # --- 관계 ---
    rel = defaultdict(lambda: defaultdict(list))
    for src, dst, typ, conf in db.execute(
            "SELECT src, dst, type, MAX(confidence) FROM relation WHERE type IN ('antonym','synonym','honorific_of','humble_of','polite_of') "
            "AND confidence >= ? GROUP BY src, dst, type", (min_rel,)):
        a, b = src.split("#")[0], dst.split("#")[0]
        if a in nid and b in nid and a != b:
            k = REL_TYPES[typ]
            if typ in ("honorific_of", "humble_of", "polite_of"):
                rel[a][k].append((conf, b))                  # a가 b의 경어
                rel[b][k + "_of"].append((conf, a))          # b의 경어 대응
            else:
                rel[a][k].append((conf, b))
                if typ == "antonym":
                    rel[b][k].append((conf, a))

    def ref(lid, conf):
        v = info[lid]
        r = [nid[lid], v[1]]
        if v[2] and v[2] != v[1]:
            r.append(v[2])
        else:
            r.append("")
        r.append(round(conf, 2))
        return r

    tmp_path = ROOT / "work/slim_tmp.sqlite"
    tmp_path.parent.mkdir(exist_ok=True)
    tmp_path.unlink(missing_ok=True)
    tmp = sqlite3.connect(tmp_path)
    tmp.execute("PRAGMA journal_mode=OFF")
    tmp.execute("PRAGMA synchronous=OFF")
    tmp.execute("CREATE TABLE lex (n INTEGER, shard INTEGER, js TEXT)")
    tmp.execute("CREATE TABLE idx (h INTEGER, shard INTEGER, key TEXT, hit TEXT)")

    # --- 뜻 + 상세 ---
    cur_id, cur_senses = None, []
    n_ex = 0

    def flush_lexeme(lid, senses):
        nonlocal n_ex
        v = info[lid]
        lang, lemma, reading, hanzi, pos, reg, level, score, source = v
        d = {"i": lid, "l": lemma}
        if reading and reading != lemma:
            d["r"] = reading
        if hanzi and hanzi != lemma:
            d["z"] = hanzi
        if pos:
            d["p"] = pos
        if reg:
            d["g"] = reg
        if level:
            lv = {k: level[k] for k in ("nf", "common", "krdict") if k in level}
            if lv:
                d["v"] = lv
        sl = []
        for ord_, definition, glosses, sreg, labels, examples in senses:
            s = {}
            if definition:
                s["d"] = definition[:400]
            gl = json.loads(glosses) if glosses else {}
            gl = {k: v for k, v in gl.items() if v}
            if gl:
                s["e"] = gl
            if sreg:
                s["g"] = sreg
            if labels:
                lb = json.loads(labels)
                lb.pop("restrict", None)
                lb.pop("pattern", None)
                if lb:
                    s["b"] = lb
            if examples:
                ex = [{"t": e.get("text", "")[:200], **({"x": e["translation"][:200]} if e.get("translation") else {})}
                      for e in json.loads(examples) if e.get("text")][:MAX_EXAMPLES]
                if ex:
                    s["x"] = ex
                    n_ex += len(ex)
            if s:
                sl.append(s)
        if sl:
            d["s"] = sl
        t = {}
        for lg, lst in trans.get(lid, {}).items():
            lst.sort(key=lambda x: (-x[0], -info[x[1]][7]))
            t[lg] = [ref(b, c) + [m] for c, b, m in lst[:top_per_lang]]
        if t:
            d["t"] = t
        r = {}
        for k, lst in rel.get(lid, {}).items():
            lst.sort(key=lambda x: (-x[0], -info[x[1]][7]))
            r[k] = [ref(b, c) for c, b in lst[:6]]
        if r:
            d["q"] = r
        tmp.execute("INSERT INTO lex (n, js) VALUES (?, ?)", (nid[lid], dumps(d)))

    wanted = set(nid)
    for sid, lid, ord_, definition, glosses, sreg, labels, examples in db.execute(
            "SELECT id, lexeme_id, ord, definition, glosses, register, labels, examples FROM sense ORDER BY lexeme_id, ord"):
        if lid not in wanted:
            continue
        v = info[lid]
        if v[0] == "en" and "#wn:" not in sid:
            continue                         # 영어는 WordNet 뜻풀이만(EJDict·kaikki 뜻은 대역어가 이미 연결로 있다)
        if lid != cur_id:
            if cur_id is not None:
                flush_lexeme(cur_id, cur_senses)
                wanted.discard(cur_id)
            cur_id, cur_senses = lid, []
        if v[0] == "en" and len(cur_senses) >= 3:
            continue
        cur_senses.append((ord_, definition, glosses, sreg, labels, examples))
    if cur_id is not None:
        flush_lexeme(cur_id, cur_senses)
        wanted.discard(cur_id)
    for lid in list(wanted):                 # 뜻이 없는 표제어(번역만 있는 en 등)
        flush_lexeme(lid, [])
    tmp.commit()
    log(f"lexeme details built ({n_ex:,} examples)")
    stats["examples"] = n_ex

    # --- 검색 색인 ---
    feat_ids, feat_list = {}, [""]
    feat_ids[""] = 0
    where = "" if with_rule_forms else f"AND source NOT IN ({','.join(repr(s) for s in RULE_SOURCES_HEAVY)})"
    seen = set()
    n_forms = 0
    rows = db.execute(f"SELECT key, lexeme_id, kind, features, via FROM form WHERE 1 = 1 {where}")
    for key, lid, kind, features, via in rows:
        n = nid.get(lid)
        if not n or kind not in KIND_CODE or not key:
            continue
        kc = KIND_CODE[kind]
        fc = feature_code(features)
        if fc not in feat_ids:
            feat_ids[fc] = len(feat_list)
            feat_list.append(fc)
        vn = nid.get(via, 0) if via else 0
        k = (key, n, kc, feat_ids[fc], vn)
        if k in seen:
            continue
        seen.add(k)
        tmp.execute("INSERT INTO idx (h, key, hit) VALUES (?, ?, ?)", (fnv1a(key), key, dumps([n, kc, feat_ids[fc]] + ([vn] if vn else []))))
        n_forms += 1
    del seen
    tmp.commit()
    stats["index_rows"] = n_forms
    log(f"index rows {n_forms:,}")

    # --- 샤드 수 결정 후 쓰기 ---
    lex_bytes = tmp.execute("SELECT SUM(LENGTH(js)) FROM lex").fetchone()[0]
    idx_bytes = tmp.execute("SELECT SUM(LENGTH(key) + LENGTH(hit) + 6) FROM idx").fetchone()[0]
    n_lex = pow2_at_least(lex_bytes / TARGET_SHARD_BYTES)
    n_idx = pow2_at_least(idx_bytes / TARGET_SHARD_BYTES)
    tmp.execute(f"UPDATE lex SET shard = n % {n_lex}")
    tmp.execute(f"UPDATE idx SET shard = h % {n_idx}")
    tmp.execute("CREATE INDEX lex_shard ON lex(shard)")
    tmp.execute("CREATE INDEX idx_shard ON idx(shard, key)")
    sizes = {"lex": [], "idx": []}
    for s in range(n_lex):
        parts = [f'"{n}":{js}' for n, js in tmp.execute("SELECT n, js FROM lex WHERE shard = ? ORDER BY n", (s,))]
        text = "{" + ",".join(parts) + "}"
        (out_dir / "lex" / f"{s}.json").write_text(text, encoding="utf-8")
        sizes["lex"].append(len(text.encode("utf-8")))
    rank_of = lambda hit: KIND_RANK[json.loads(hit)[1]]
    for s in range(n_idx):
        by_key = defaultdict(list)
        for key, hit in tmp.execute("SELECT key, hit FROM idx WHERE shard = ?", (s,)):
            by_key[key].append(json.loads(hit))
        obj = {}
        for key, hits in by_key.items():
            hits.sort(key=lambda h: (KIND_RANK[h[1]], -info[include[h[0] - 1]][7]))
            obj[key] = hits[:MAX_HITS_PER_KEY]
        text = dumps(obj)
        (out_dir / "idx" / f"{s}.json").write_text(text, encoding="utf-8")
        sizes["idx"].append(len(text.encode("utf-8")))
    manifest = {
        "version": time.strftime("%Y.%m.%d"), "data": "anikan-ENJPKR-dictionary", "shards": {"lex": n_lex, "idx": n_idx},
        "hash": "fnv1a32-utf8; shard = hash % shards.idx; lexeme shard = n % shards.lex",
        "kinds": KIND_NAMES, "features": feat_list, "lexemes": len(include),
        "excluded": {"methods": list(EXCLUDE_METHODS), "rule_forms": [] if with_rule_forms else list(RULE_SOURCES_HEAVY)},
        "attribution": "ATTRIBUTION.md",
        "legend": {"lex": {"i": "id", "l": "lemma", "r": "reading", "z": "hanzi", "p": "pos", "g": "register", "v": "level",
                           "s": "senses[d definition, e glosses{lang:[..]}, g register, b labels, x examples[t text, x translation]]",
                           "t": "translations{lang:[[n, lemma, reading, conf, methods]]}",
                           "q": "relations{ant, syn, hon (this is honorific of), hum, pol, hon_of (honorific counterparts) ...: [[n, lemma, reading, conf]]}"},
                   "idx": "key -> [[n, kind, feature, via?]] ; kind/feature index into kinds/features"},
    }
    (out_dir / "manifest.json").write_text(dumps(manifest), encoding="utf-8")
    stats["shards"] = {"lex": n_lex, "idx": n_idx}
    stats["bytes"] = {"lex": sum(sizes["lex"]), "idx": sum(sizes["idx"]), "max_lex_shard": max(sizes["lex"]), "max_idx_shard": max(sizes["idx"])}
    stats["bytes"]["total"] = stats["bytes"]["lex"] + stats["bytes"]["idx"]
    tmp.close()
    tmp_path.unlink(missing_ok=True)
    stats["seconds"] = round(time.time() - t0)
    (out_dir / "slim_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(OUT / "anikan.sqlite"))
    ap.add_argument("--out", default=str(OUT / "site/data"))
    ap.add_argument("--no-rule-forms", action="store_true", help="규칙 생성 활용형을 빼고 만든다(-38MB, 대신 브라우저에서 같은 규칙으로 생성해야 お書きになる 같은 형태를 찾음)")
    ap.add_argument("--min-conf", type=float, default=0.7)
    a = ap.parse_args()
    s = run(a.db, a.out, with_rule_forms=not a.no_rule_forms, min_conf=a.min_conf)
    print(json.dumps(s, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
