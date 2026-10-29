"""활용·경어 생성기를 표제어에 적용해 form 줄을 더하고, 이미 있는 원본 활용형과 겹치는 단어로 정확도를 잰다(§6.2, §10 4단계)."""
import json
from collections import defaultdict

from anikan.common import search_key
from anikan.inflect import ja, ko


def _known_forms(db, lang):
    known = defaultdict(set)
    for lid, surface, src in db.execute("SELECT lexeme_id, surface, source FROM form WHERE lang = ? AND kind IN ('inflection','honorific_inflection')", (lang,)):
        known[lid].add(surface)
    return known


def run_ko(sink, stats):
    db = sink.db
    known = _known_forms(db, "ko")
    by_lemma = defaultdict(list)
    rows = list(db.execute("SELECT id, lemma, pos, register FROM lexeme WHERE lang = 'ko' AND pos IN ('verb','adj')"))
    for lid, lemma, pos, reg in rows:
        by_lemma[lemma].append(lid)
    cls_updates = []
    gen_honor = gen_formal = 0
    # 정확도: (1) 합쇼체 현재형 (2) 높임형 — 원본이 이미 가진 활용형과 비교
    ev = {"formal_n": 0, "formal_hit": 0, "hon_n": 0, "hon_hit": 0, "hon_pop": 0}
    cls_count = defaultdict(int)
    for lid, lemma, pos, reg in rows:
        if not lemma.endswith("다") or " " in lemma or len(lemma) < 2:
            continue
        kf = known.get(lid, set())
        cls = ko.classify(lemma, kf)
        if not cls:
            continue
        cls_count[cls] += 1
        cls_updates.append((cls, lid))
        # 합쇼체
        fp = ko.formal_present(lemma)
        # 철자형만 비교한다: 기초사전 활용 예에는 발음 표기(함니다·감니다)가 섞여 있다
        cands = {f for f in kf if f.endswith("니다") and len(f) >= 3 and (f.endswith("습니다") or ko.final(f[-3]) == "ㅂ")
                 and not f.endswith(("었습니다", "았습니다", "였습니다", "겠습니다", "했습니다"))
                 and not (len(f) > 3 and ko.final(f[-4]) == "ㅆ")}
        if cands:
            ev["formal_n"] += 1
            ev["formal_hit"] += fp in cands
        if fp not in kf:
            sink.add("form", key=search_key(fp, "ko"), surface=fp, lang="ko", lexeme_id=lid, kind="inflection",
                     features={"politeness": "formal", "tense": "present", "speech_level": "hapsyo"}, via=None, source="rule:ko-hapsyo")
            gen_formal += 1
        # 높임 (-시-). 이미 '-시다' 꼴이거나 경어 표제어는 건너뛴다
        if lemma.endswith("시다") or reg in ("honorific", "humble"):
            continue
        hf = ko.honorific_forms(lemma, cls)
        if not hf:
            continue
        hs = ko.honorific_stem(lemma, cls)
        for surf, feat in hf:
            sink.add("form", key=search_key(surf, "ko"), surface=surf, lang="ko", lexeme_id=lid,
                     kind="honorific_inflection", features=feat, via=None, source="rule:ko-si")
            gen_honor += 1
    # 높임 평가: 실제 높임 활용표(…세요 꼴)가 있는 -시다 표제어 H를 모집단으로, H의 어간을 만드는 V가 생성한 형태가 H의 활용표에 있는지
    gen_by_stem = defaultdict(list)
    for lid, lemma, pos, reg in rows:
        if lemma.endswith("다") and not lemma.endswith("시다") and reg not in ("honorific", "humble") and len(lemma) > 1:
            cls = ko.classify(lemma, known.get(lid, set()))
            hs = ko.honorific_stem(lemma, cls) if cls else None
            if hs:
                gen_by_stem[hs + "다"].append((lemma, cls))
    covered = 0
    for lid, lemma, pos, reg in rows:
        hk = known.get(lid, set())
        if lemma.endswith("시다") and any(f.endswith("세요") for f in hk):
            ev["hon_pop"] = ev.get("hon_pop", 0) + 1
            vs = gen_by_stem.get(lemma)
            if not vs:
                continue
            covered += 1
            for vl, vc in vs[:1]:
                test = [x for x, _ in ko.honorific_forms(vl, vc) if x.endswith(("세요", "십니다", "셨어요", "셨습니다"))]
                ev["hon_n"] += len(test)
                ev["hon_hit"] += sum(1 for x in test if x in hk)
    ev["hon_covered"] = covered
    db.executemany("UPDATE lexeme SET infl_class = ? WHERE id = ?", cls_updates)
    sink.flush()
    stats["ko_gen_honorific_forms"], stats["ko_gen_formal_forms"] = gen_honor, gen_formal
    stats["ko_class"] = dict(cls_count)
    stats["ko_eval"] = ev


def run_ja(sink, stats):
    db = sink.db
    known = _known_forms(db, "ja")
    rows = list(db.execute("SELECT id, lemma, infl_class, register, reading FROM lexeme WHERE lang = 'ja' AND source = 'jmdict' "
                           "AND infl_class IS NOT NULL"))
    gen_pol = gen_keigo = 0
    ev = {"polite_n": 0, "polite_hit": 0}
    for lid, lemma, infl, reg, reading in rows:
        if ja.base_class(infl) is None:
            continue
        kf = known.get(lid, set())
        surfaces = [lemma] + ([reading] if reading and reading != lemma and ja.KANA_ONLY.match(reading) else [])
        hit = False
        kmas = {f for f in kf if f.endswith("ます") and not f.endswith(("ましょう",))}
        for base in surfaces:
            forms = ja.polite_forms(base, infl)
            mas = next((x for x, f in forms if f.get("politeness") == "polite" and f.get("tense") == "present"), None)
            hit = hit or (mas in kmas if mas else False)
            for surf, feat in forms:
                if surf in kf:
                    continue
                sink.add("form", key=search_key(surf, "ja"), surface=surf, lang="ja", lexeme_id=lid, kind="inflection",
                         features=feat, via=None, source="rule:ja-masu")
                gen_pol += 1
        if kmas:
            ev["polite_n"] += 1
            ev["polite_hit"] += hit
        if reg in ("honorific", "humble"):
            continue
        for base in surfaces:
            for surf, kind, feat in ja.keigo_forms(base, infl):
                sink.add("form", key=search_key(surf, "ja"), surface=surf, lang="ja", lexeme_id=lid, kind="honorific_inflection",
                         features={**feat, "keigo": kind, "honorific": kind == "honorific", "humble": kind == "humble"},
                         via=None, source="rule:ja-keigo")
                gen_keigo += 1
    sink.flush()
    stats["ja_gen_polite_forms"], stats["ja_gen_keigo_forms"], stats["ja_eval"] = gen_pol, gen_keigo, ev


def run_ko_romaja(sink, stats):
    """한국어 표제어의 로마자 색인(`romaji`)을 규칙으로 만들고, kaikki가 가진 로마자 표기와 겹치는 단어로 정확도를 잰다."""
    from anikan.inflect.ko_romaja import romanize
    from anikan.normalize.romaji import romaji_key
    db = sink.db
    known = defaultdict(set)
    for lid, surface in db.execute("SELECT lexeme_id, surface FROM form WHERE lang = 'ko' AND kind = 'romaji' AND source = 'kaikki'"):
        known[lid].add(romaji_key(surface))
    n = ev_n = ev_hit = 0
    for lid, lemma in db.execute("SELECT id, lemma FROM lexeme WHERE lang = 'ko' AND lemma GLOB '*[가-힣]*'"):
        r = romanize(lemma)
        key = romaji_key(r)
        if not key:
            continue
        if lid in known:
            ev_n += 1
            ev_hit += key in known[lid]
        if key not in known.get(lid, ()):
            sink.add("form", key=key, surface=r, lang="ko", lexeme_id=lid, kind="romaji", features=None, via=None, source="rule:ko-rr")
            n += 1
    sink.flush()
    stats["ko_romaja_forms"] = n
    stats["ko_romaja_eval"] = {"n": ev_n, "hit": ev_hit}
