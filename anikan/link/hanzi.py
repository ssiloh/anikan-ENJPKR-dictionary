"""한자 일치(§5 #3): 신자체·번체를 맞춘 hanzi_norm이 같고 영어 풀이가 겹치면 높게, 안 겹치면 거짓 친구 의심으로 낮게."""
from collections import defaultdict


def hanzi_match(sink, stats):
    db = sink.db
    ja_by, ko_by = defaultdict(list), defaultdict(list)
    for lid, lang, hn in db.execute("SELECT id, lang, hanzi_norm FROM lexeme WHERE hanzi_norm IS NOT NULL AND lang IN ('ja','ko')"):
        (ja_by if lang == "ja" else ko_by)[hn].append(lid)
    # 영어 풀이 집합: ja는 jmdict_gloss, ko는 krdict_equivalent(영어)
    en_of = defaultdict(set)
    for src, dst in db.execute("SELECT src, dst FROM link WHERE method = 'jmdict_gloss' OR (method = 'krdict_equivalent' AND dst LIKE 'en:%')"):
        en_of[src.split("#")[0]].add(dst)
    # 영어 풀이가 없는 쪽(EJDict만 있는 경우 등)은 판단 보류 → 0.6
    ok = false_friend = unknown = 0
    for hn, kos in ko_by.items():
        jas = ja_by.get(hn)
        if not jas or len(jas) > 12:
            continue
        for k in kos:
            ek = en_of.get(k)
            for j in jas:
                ej = en_of.get(j)
                if ek and ej:
                    if ek & ej:
                        conf, ev = 0.85, "hanzi+english"
                        ok += 1
                    else:
                        conf, ev = 0.4, "hanzi only (false friend?)"
                        false_friend += 1
                else:
                    conf, ev = 0.6, "hanzi, no english to check"
                    unknown += 1
                sink.add("link", src=k, dst=j, kind="translation", method="hanzi_match", confidence=conf,
                         evidence=hn if ev == "hanzi+english" else f"{hn} / {ev}", sources=["krdict", "jmdict"])
    sink.flush()
    stats["hanzi_match_ok"], stats["hanzi_match_false_friend"], stats["hanzi_match_unchecked"] = ok, false_friend, unknown
