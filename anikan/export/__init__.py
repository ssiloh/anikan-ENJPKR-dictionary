"""내보내기(§7): SQLite 마무리 · pairs/*.jsonl|tsv · forms/*.tsv · stats.md."""
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

from anikan.common import OUT, dumps

PAIRS = [("ja", "ko"), ("ko", "ja"), ("en", "ja"), ("ja", "en"), ("en", "ko"), ("ko", "en")]
MIN_EXPORT = 0.5      # 기본 내보내기 하한(§5)
MIN_TSV = 0.7


def finalize_db(db, stats):
    """form 중복 제거: 같은 (key, lexeme, kind)는 하나, 이미 표제어·읽기로 있는 변형 줄은 뺀다."""
    before = db.execute("SELECT COUNT(*) FROM form").fetchone()[0]
    db.execute("DELETE FROM form WHERE rowid NOT IN (SELECT MIN(rowid) FROM form GROUP BY key, lexeme_id, kind)")
    db.execute("DELETE FROM form WHERE kind = 'variant' AND EXISTS (SELECT 1 FROM form f2 WHERE f2.key = form.key AND "
               "f2.lexeme_id = form.lexeme_id AND f2.kind IN ('lemma','reading'))")
    db.execute("DELETE FROM form WHERE kind IN ('inflection','honorific_inflection') AND EXISTS (SELECT 1 FROM form f2 WHERE "
               "f2.key = form.key AND f2.lexeme_id = form.lexeme_id AND f2.kind IN ('lemma','reading','variant'))")
    db.commit()
    stats["form_dedup_removed"] = before - db.execute("SELECT COUNT(*) FROM form").fetchone()[0]


def lex_edges(db):
    """link를 표제어 단위로 모은다: (a, b) → {방법: (신뢰도, 근거)}. 방향 없는 연결로 본다."""
    info = {r[0]: r[1:] for r in db.execute("SELECT id, lang, lemma, reading, pos, register, level, score FROM lexeme")}
    edges = defaultdict(dict)
    unlinked = defaultdict(list)
    for src, dst, method, conf, ev in db.execute(
            "SELECT src, dst, method, confidence, evidence FROM link WHERE kind = 'translation'"):
        a, b = src.split("#")[0], dst.split("#")[0]
        if b.startswith(("ja:unlinked", "ko:unlinked")):
            unlinked[a].append((b.split(":", 2)[2], method, conf, b.split(":", 1)[0]))
            continue
        if a not in info or b not in info or a == b or info[a][0] == info[b][0]:
            continue
        for x, y in ((a, b), (b, a)):
            cur = edges[(x, y)].get(method)
            if not cur or conf > cur[0]:
                edges[(x, y)][method] = (conf, ev)
    return info, edges, unlinked


def combine(by_method):
    rest = 1.0
    for conf, _ in by_method.values():
        rest *= 1 - conf
    return 1 - rest


def write_pairs(db, out_dir, stats):
    out_dir = Path(out_dir)
    (out_dir / "pairs").mkdir(parents=True, exist_ok=True)
    info, edges, unlinked = lex_edges(db)
    rel = defaultdict(list)
    for src, dst, typ, method, conf in db.execute(
            "SELECT src, dst, type, method, confidence FROM relation WHERE type IN "
            "('antonym','synonym','honorific_of','humble_of','polite_of') AND confidence >= 0.5"):
        a, b = src.split("#")[0], dst.split("#")[0]
        if a in info and b in info:
            rel[a].append((typ, b, method, conf, "out"))
            rel[b].append((typ, a, method, conf, "in"))
    by_src = defaultdict(list)
    for (a, b), m in edges.items():
        by_src[a].append((b, m))
    counts = {}
    for sl, tl in PAIRS:
        n = n_tsv = 0
        sense_stmt = "SELECT id, definition, glosses, register FROM sense WHERE lexeme_id = ? ORDER BY ord"
        with open(out_dir / "pairs" / f"{sl}-{tl}.jsonl", "w", encoding="utf-8") as jf, \
                open(out_dir / "pairs" / f"{sl}-{tl}.tsv", "w", encoding="utf-8") as tf:
            for a, targets in sorted(by_src.items()):
                ia = info[a]
                if ia[0] != sl:
                    continue
                tg = []
                for b, m in targets:
                    ib = info[b]
                    if ib[0] != tl:
                        continue
                    c = combine(m)
                    if c >= MIN_EXPORT:
                        tg.append({"id": b, "lemma": ib[1], "reading": ib[2], "pos": ib[3], "confidence": round(c, 3),
                                   "methods": {k: round(v[0], 2) for k, v in m.items()},
                                   "evidence": [v[1] for v in m.values() if v[1]][:3]})
                if not tg:
                    continue
                tg.sort(key=lambda r: -r["confidence"])
                rec = {"id": a, "lang": sl, "lemma": ia[1], "reading": ia[2], "pos": ia[3], "register": ia[4],
                       "level": json.loads(ia[5]) if ia[5] else None,
                       "senses": [{"id": s[0], "definition": s[1], "glosses": json.loads(s[2]) if s[2] else None, "register": s[3]}
                                  for s in db.execute(sense_stmt, (a,))][:12],
                       "translations": tg,
                       "unlinked": [{"text": t, "method": m, "confidence": c} for t, m, c, lg in unlinked.get(a, []) if lg == tl][:8],
                       "antonyms": [{"id": b, "lemma": info[b][1], "method": m, "confidence": c}
                                    for t, b, m, c, d in rel[a] if t == "antonym"][:8],
                       "synonyms": [{"id": b, "lemma": info[b][1], "method": m, "confidence": c}
                                    for t, b, m, c, d in rel[a] if t == "synonym"][:8],
                       "honorific": [{"relation": t if d == "out" else t + "(reverse)", "id": b, "lemma": info[b][1], "method": m,
                                      "confidence": c} for t, b, m, c, d in rel[a] if t.endswith("_of")][:8]}
                jf.write(dumps(rec) + "\n")
                n += 1
                good = [t for t in tg if t["confidence"] >= MIN_TSV]
                if good:
                    shown = "; ".join(t["lemma"] + (f"({t['reading']})" if t["reading"] and t["reading"] != t["lemma"] else "")
                                      for t in good[:8])
                    tf.write("\t".join([ia[1], ia[2] or "", shown]) + "\n")
                    n_tsv += 1
        counts[f"{sl}-{tl}"] = {"entries": n, "tsv_entries": n_tsv}
    stats["pairs"] = counts


def write_forms(db, out_dir, stats):
    out_dir = Path(out_dir)
    (out_dir / "forms").mkdir(parents=True, exist_ok=True)
    lemma = dict(db.execute("SELECT id, lemma FROM lexeme WHERE lang IN ('ja','ko')"))
    counts = {}
    for lang in ("ja", "ko"):
        n = 0
        with open(out_dir / "forms" / f"{lang}.tsv", "w", encoding="utf-8") as f:
            f.write("surface\tkey\tlexeme_id\tlemma\tkind\tfeatures\tvia\tsource\n")
            for key, surface, lid, kind, feat, via, src in db.execute(
                    "SELECT key, surface, lexeme_id, kind, features, via, source FROM form WHERE lang = ? AND kind IN "
                    "('inflection','honorific_inflection','lexical_honorific') ORDER BY key", (lang,)):
                f.write("\t".join([surface, key, lid, lemma.get(lid, ""), kind, feat or "", via or "", src]) + "\n")
                n += 1
        counts[lang] = n
    stats["forms_tsv"] = counts


def write_stats_md(db, stats, path):
    q = lambda s, *a: db.execute(s, a).fetchall()
    L = ["# stats", "", "빌드마다 `python -m anikan.build`가 다시 쓴다.", ""]
    L += ["## 표제어", "", "| 언어 | 원본 | 표제어 |", "|---|---|---|"]
    for lang, src, n in q("SELECT lang, source, COUNT(*) FROM lexeme GROUP BY lang, source ORDER BY lang, 3 DESC"):
        L.append(f"| {lang} | {src} | {n:,} |")
    L += ["", "## 연결(link) — 방법별", "", "| kind | method | 줄 수 | 평균 신뢰도 | 0.7 이상 |", "|---|---|---|---|---|"]
    for k, m, n, a, g in q("SELECT kind, method, COUNT(*), AVG(confidence), SUM(confidence >= 0.7) FROM link GROUP BY kind, method ORDER BY kind, 3 DESC"):
        L.append(f"| {k} | {m} | {n:,} | {a:.2f} | {g:,} |")
    L += ["", "## 관계(relation)", "", "| type | method | 줄 수 |", "|---|---|---|"]
    for t, m, n in q("SELECT type, method, COUNT(*) FROM relation GROUP BY type, method ORDER BY 3 DESC"):
        L.append(f"| {t} | {m} | {n:,} |")
    L += ["", "## 검색 색인(form)", "", "| 언어 | kind | 줄 수 |", "|---|---|---|"]
    for lang, k, n in q("SELECT lang, kind, COUNT(*) FROM form GROUP BY lang, kind ORDER BY lang, 3 DESC"):
        L.append(f"| {lang} | {k} | {n:,} |")
    ev = stats.get("ko_eval", {})
    jev = stats.get("ja_eval", {})
    L += ["", "## 활용 생성 정확도 (원본 활용형과 겹치는 단어 기준)", "",
          "| 항목 | 맞음 / 비교 대상 | 비율 |", "|---|---|---|"]
    def row(name, hit, n):
        return f"| {name} | {hit:,} / {n:,} | {hit / n:.1%} |" if n else f"| {name} | - | - |"
    L.append(row("한국어 합쇼체 현재(-ㅂ니다/-습니다)", ev.get("formal_hit", 0), ev.get("formal_n", 0)))
    L.append(row("일본어 ます형", jev.get("polite_hit", 0), jev.get("polite_n", 0)))
    rv = stats.get("ko_romaja_eval", {})
    L.append(row("한국어 로마자(국어의 로마자 표기법) — kaikki 표기와 일치", rv.get("hit", 0), rv.get("n", 0)))
    L.append(row("한국어 높임(-시-) — 실제 높임 활용표가 있는 -시다 표제어만", ev.get("hon_hit", 0), ev.get("hon_n", 0)))
    L += ["", f"한국어 높임 비교 모집단은 {ev.get('hon_pop', 0)}개 표제어뿐이고(kaikki에 `-시다` 활용표가 거의 없음), "
          f"틀린 건 어간이 우연히 `-시다`인 일반 동사(꼬시다·마시다·쑤시다·부시다)와의 철자 중복이다.", ""]
    L += ["", "## 커버리지", ""]
    r = q("SELECT COUNT(*), SUM(EXISTS(SELECT 1 FROM link l JOIN sense s ON s.id = l.src WHERE s.lexeme_id = lexeme.id AND "
          "l.dst LIKE 'ja:%' AND l.confidence >= 0.7)) FROM lexeme WHERE source = 'krdict' AND json_extract(level, '$.n') = 1")
    if r and r[0][0]:
        L.append(f"- 기초사전 초급 어휘 {r[0][0]:,}개 중 일본어 연결(0.7↑)이 있는 것: {r[0][1]:,} ({r[0][1] / r[0][0]:.1%})")
    r = q("SELECT COUNT(*), SUM(EXISTS(SELECT 1 FROM link WHERE (src = lexeme.id AND dst LIKE 'ko:%' OR dst = lexeme.id AND src LIKE 'ko:%') "
          "AND confidence >= 0.5)) FROM lexeme WHERE source = 'jmdict' AND level LIKE '%\"common\"%'")
    if r and r[0][0]:
        L.append(f"- JMdict 상용어(우선순위 태그) {r[0][0]:,}개 중 한국어 연결(0.5↑)이 있는 것: {r[0][1]:,} ({r[0][1] / r[0][0]:.1%})")
    r = q("SELECT COUNT(*), SUM(EXISTS(SELECT 1 FROM form f WHERE f.lexeme_id = lexeme.id AND f.kind = 'honorific_inflection')) "
          "FROM lexeme WHERE lang = 'ko' AND source = 'krdict' AND pos IN ('verb','adj') AND lemma LIKE '%다'")
    if r and r[0][0]:
        L.append(f"- 기초사전 동사·형용사 {r[0][0]:,}개 중 높임 활용 색인이 있는 것: {r[0][1]:,} ({r[0][1] / r[0][0]:.1%})")
    L += ["", "## 빌드 수치 (원본 대조)", "", "```json", json.dumps(stats, ensure_ascii=False, indent=1, default=str), "```", ""]
    Path(path).write_text("\n".join(L), encoding="utf-8")
