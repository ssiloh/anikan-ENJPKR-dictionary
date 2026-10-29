"""영어 gloss 기반 연결: jmdict_gloss(§5 #1) · wn_concept(#5) · en_pivot(#4)."""
import json
import math
import re
from collections import defaultdict

from anikan.lexindex import pos_compatible

LEAD = re.compile(r"^(to |be |a |an |the )")
STOP = {"of", "the", "a", "an", "to", "in", "on", "for", "and", "or", "with", "be", "is", "one", "ones", "something",
        "someone", "etc", "by", "from", "as", "at", "that", "it", "oneself", "into", "not", "up", "out"}
WN_POS = {"noun": "n", "name": "n", "verb": "v", "adj": "a", "adj-na": "a", "adv": "r"}


def gloss_keys(g):
    """gloss 한 개 → 영어 표제어 후보(`en:` 아님, 소문자 문자열) 목록. 긴 설명문은 후보 없음."""
    t = re.sub(r"\([^)]*\)|\[[^\]]*\]", "", g).strip().lower().strip(" .;,")
    if not t or len(t.split()) > 4 or any(c in t for c in ",;/"):
        return []
    short = LEAD.sub("", t)
    return list(dict.fromkeys([t, short])) if short else [t]


def content_words(text):
    return {w for w in re.findall(r"[a-z]+", (text or "").lower()) if w not in STOP and len(w) > 2}


def _senses(db, where):
    cur = db.execute(f"SELECT s.id, s.lexeme_id, s.glosses, s.definition, s.extra, l.pos FROM sense s "
                     f"JOIN lexeme l ON l.id = s.lexeme_id WHERE {where}")
    yield from cur


def jmdict_gloss(sink, en_lex, stats):
    n = 0
    for sid, lex, glosses, _d, _x, pos in _senses(sink.db, "s.id LIKE 'ja:jmdict:%'"):
        seen = set()
        for g in json.loads(glosses).get("en", []):
            for k in gloss_keys(g):
                lid = "en:" + k
                if lid in en_lex and lid not in seen:
                    seen.add(lid)
                    sink.add("link", src=sid, dst=lid, kind="translation", method="jmdict_gloss", confidence=0.9,
                             evidence=g, sources=["jmdict"])
                    n += 1
                    break
    sink.flush()
    stats["jm_gloss_links"] = n


def wn_concept(sink, en, stats):
    """ja/ko 뜻의 영어 대역어 → WordNet synset. 후보가 하나뿐이면 높게, 여럿이면 빈도 순위와 풀이 겹침으로 점수."""
    n = 0
    where = "s.id LIKE 'ja:jmdict:%' OR s.id LIKE 'ko:krdict:%'"
    for sid, lex, glosses, definition, extra, pos in _senses(sink.db, where):
        wpos = WN_POS.get(pos)
        if not wpos:
            continue
        g = json.loads(glosses).get("en", [])
        if not g:
            continue
        ex = json.loads(extra) if extra else {}
        ctx = content_words(" ".join(g)) | content_words(ex.get("definition_en"))
        best = {}
        for gl in g:
            for k in gloss_keys(gl):
                syn = en.synsets_by_lemma.get((k, wpos))
                if not syn:
                    continue
                for rank, ss in enumerate(syn[:6]):
                    base = 0.8 if len(syn) == 1 else max(0.3, 0.65 - 0.12 * rank)
                    words = content_words(en.concept_gloss.get(ss, "")) | {w.lower() for l in en.concept_words.get(ss, []) for w in l.split()}
                    others = ctx - set(k.split())
                    bonus = 0.2 if others & words else 0
                    c = min(0.9, base + bonus)
                    if c > best.get(ss, 0):
                        best[ss] = c
                break
        for ss, c in sorted(best.items(), key=lambda kv: -kv[1])[:2]:
            if c >= 0.4:
                sink.add("link", src=sid, dst=ss, kind="concept", method="wn_concept", confidence=round(c, 2),
                         evidence=None, sources=["wordnet"] + (["jmdict"] if sid.startswith("ja:") else ["krdict"]))
                n += 1
    sink.flush()
    stats["wn_concept_links"] = n


def en_pivot(sink, stats):
    """같은 영어 표제어에 연결된 일본어 뜻과 한국어 뜻을 이어 준다(IDF 식 가중, 일반적인 영어일수록 낮게)."""
    ja_by_en, ko_by_en = defaultdict(list), defaultdict(list)
    for src, dst in sink.db.execute("SELECT src, dst FROM link WHERE method = 'jmdict_gloss'"):
        ja_by_en[dst].append(src)
    for src, dst in sink.db.execute("SELECT src, dst FROM link WHERE method = 'krdict_equivalent' AND dst LIKE 'en:%'"):
        ko_by_en[dst].append(src)
    pos = dict(sink.db.execute("SELECT id, pos FROM lexeme WHERE lang IN ('ja','ko')"))
    acc = defaultdict(lambda: 1.0)
    for e, jas in ja_by_en.items():
        kos = ko_by_en.get(e)
        if not kos or len(jas) * len(kos) > 120:
            continue
        c = 0.6 / (1 + 0.1 * (len(jas) * len(kos) - 1))
        for k in kos:
            kp = pos.get(k.split("#")[0])
            for j in jas:
                if pos_compatible(kp, pos.get(j.split("#")[0])):
                    acc[(k, j)] *= 1 - c
    n = 0
    for (k, j), rest in acc.items():
        conf = min(0.7, 1 - rest)
        if conf >= 0.3:
            sink.add("link", src=k, dst=j, kind="translation", method="en_pivot", confidence=round(conf, 2),
                     evidence=None, sources=["krdict", "jmdict"])
            n += 1
    sink.flush()
    stats["en_pivot_links"] = n
