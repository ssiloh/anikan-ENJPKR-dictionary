"""어휘적 경어 관계(§6.1): 핵심 대응표(curated) + 같은 영어 gloss·대역어 일치(definition).
이미 원본이 준 관계(source)와 뜻풀이 한 단어 관계(definition)는 normalize 단계에서 들어와 있다."""
import json
from collections import defaultdict

from anikan.common import MAPPINGS, ROOT, read_tsv

HON_REG = {"honorific", "humble", "polite", "beautified"}
TYPE = {"honorific": "honorific_of", "humble": "humble_of", "polite": "polite_of"}
REL_TYPES = ("honorific_of", "humble_of", "polite_of")


def _lex_info(db):
    return {r[0]: r[1:] for r in db.execute("SELECT id, lang, lemma, pos, register, score FROM lexeme WHERE lang IN ('ja','ko')")}


def curated(sink, indexes, stats):
    db = sink.db
    info = _lex_info(db)
    existing = {(s, d, t) for s, d, t in db.execute(
        f"SELECT substr(src, 1, instr(src || '#', '#') - 1), dst, type FROM relation WHERE type IN {REL_TYPES}")}
    review = []
    ok = verified = 0

    # 뜻 단위 경어 표시가 하나라도 있는 표제어 → 그 문체 (어휘 수준 문체는 모든 뜻이 같을 때만 정해지므로)
    sense_reg = defaultdict(set)
    for lex, reg in db.execute("SELECT lexeme_id, register FROM sense WHERE register IN ('honorific','humble','polite') "
                               "AND (lexeme_id LIKE 'ja:%' OR lexeme_id LIKE 'ko:%')"):
        sense_reg[lex].add(reg)

    def pick(lang, text, want_hon):
        idx = indexes[lang]
        ids = idx.candidates(text)
        if not ids and text.endswith("する"):
            ids = idx.candidates(text[:-2])               # 拝見する → 拝見 (する 동사 명사부)
        if want_hon:
            hon = [i for i in ids if sense_reg.get(i) or info.get(i, (None,) * 5)[3] in HON_REG]
            ids = hon or ids
        else:
            plain = [i for i in ids if info.get(i, (None,) * 5)[3] not in HON_REG]
            ids = plain or ids
        return idx.best(ids)

    for row in read_tsv(MAPPINGS / "honorific_core.tsv"):
        lang, plain, hon, typ = row[:4]
        p, h = pick(lang, plain, False), pick(lang, hon, True)
        if not p or not h or p == h:
            review.append((lang, plain, hon, typ, "표제어를 찾지 못함" if not (p and h) else "같은 표제어"))
            continue
        regs = sense_reg.get(h, set()) | ({info[h][3]} if info[h][3] in HON_REG else set())
        if typ in regs or (h, p, TYPE[typ]) in existing:
            verified += 1
        elif regs & {"honorific", "humble"}:
            verified += 1        # 경어이긴 하나 높임/낮춤 분류가 다름(기초사전은 드리다를 '높임'으로 표시) — 메모만 남김
            review.append((lang, plain, hon, typ, f"유형 차이(검증은 통과): 원본 {'/'.join(sorted(regs))}"))
        else:
            review.append((lang, plain, hon, typ, f"원본 경어 표시 없음: {info[h][3]}"))
        sink.add("relation", src=h, dst=p, type=TYPE[typ], method="curated", confidence=1.0, sources=["curated"])
        ok += 1
    sink.flush()
    stats["hon_curated"], stats["hon_curated_verified"], stats["hon_curated_review"] = ok, verified, len(review)
    (ROOT / "qa").mkdir(exist_ok=True)
    with open(ROOT / "qa/honorific_review.tsv", "w", encoding="utf-8") as f:
        f.write("lang\tplain\thonorific\ttype\treason\n")
        for r in review:
            f.write("\t".join(r) + "\n")


def by_gloss(sink, stats):
    """경어 뜻(JMdict hon/hum/pol, 기초사전 높임/낮춤 표시)이 영어·일본어 대역어를 공유하는 일반 표제어를 기본형 후보로."""
    db = sink.db
    info = _lex_info(db)
    has_rel = {r[0] for r in db.execute(
        f"SELECT substr(src, 1, instr(src || '#', '#') - 1) FROM relation WHERE type IN {REL_TYPES}")}
    # 대역어(영어 표제어·일본어 표제어) → 일반(비경어) 표제어 목록
    plain_by_target = defaultdict(set)
    hon_senses = []
    sense_reg = {sid: (lex, reg) for sid, lex, reg in db.execute(
        "SELECT id, lexeme_id, register FROM sense WHERE id LIKE 'ja:jmdict:%' OR id LIKE 'ko:krdict:%'")}
    links = defaultdict(list)
    for src, dst, method, conf in db.execute(
            "SELECT src, dst, method, confidence FROM link WHERE method IN ('jmdict_gloss','krdict_equivalent') AND src NOT LIKE 'en:%'"):
        if src in sense_reg:
            links[src].append(dst)
    for sid, dsts in links.items():
        lex, reg = sense_reg[sid]
        if reg in HON_REG:
            hon_senses.append((sid, lex, reg, dsts))
        else:
            for d in dsts:
                plain_by_target[d].add(lex)
    n = 0
    done = set()
    for sid, lex, reg, dsts in hon_senses:
        if lex in has_rel or lex in done:
            continue
        lang, lemma, pos, _lreg, score = info[lex]
        votes = defaultdict(int)
        for d in dsts:
            for cand in plain_by_target.get(d, ()):
                if cand != lex and info[cand][0] == lang and info[cand][3] not in HON_REG:
                    votes[cand] += 1
        if not votes:
            continue
        ranked = sorted(votes.items(), key=lambda kv: (-kv[1], -info[kv[0]][4]))
        best, v = ranked[0]
        if info[best][4] < 40 and v < 2:
            continue                 # 드문 말과 한 번 겹친 것은 근거가 약하다
        unique = len(ranked) == 1 or ranked[1][1] < v or info[ranked[1][0]][4] < info[best][4] * 0.5
        conf = 0.8 if (v >= 2 and unique) else 0.75 if unique else 0.6
        typ = TYPE.get(reg, "honorific_of")
        sink.add("relation", src=lex, dst=best, type=typ, method="definition", confidence=conf, sources=["jmdict" if lang == "ja" else "krdict"])
        done.add(lex)
        n += 1
    sink.flush()
    stats["hon_by_gloss"] = n
