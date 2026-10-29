"""반의어 옮기기(§5.1): A ↔ B 반의어이고 A′·B′가 각각 A·B의 대역(신뢰도 0.7 이상)이면 A′ ↔ B′ 후보.
신뢰도 = 반의어 × 두 대역 신뢰도 ÷ √(A′ 후보 수 × B′ 후보 수). 'hot'처럼 일반적인 영어 한 단어에 일본어가 여럿 달린
경우 곱집합이 생기므로, 대역이 여럿일수록 낮춘다. 표제어 단위(`projected`)로 낸다."""
import math
from collections import defaultdict

MIN_LINK = 0.7
MIN_OUT = 0.5
TARGETS = {"en": ("ja", "ko"), "ja": ("ko",), "ko": ("ja",)}   # 반의어 쌍의 언어 → 옮길 언어


def _lex(x):
    return x.split("#")[0]


def project_antonyms(sink, stats):
    db = sink.db
    db.execute("DELETE FROM relation WHERE method = 'projected' AND type = 'antonym'")
    lang = {i: l for i, l in db.execute("SELECT id, lang FROM lexeme")}
    equiv = defaultdict(lambda: defaultdict(dict))       # 표제어 → 언어 → {대상: 신뢰도}
    for src, dst, conf in db.execute(
            "SELECT src, dst, MAX(confidence) FROM link WHERE kind = 'translation' AND confidence >= ? GROUP BY src, dst",
            (MIN_LINK,)):
        a, b = _lex(src), dst
        if a in lang and b in lang and a != b:
            for x, y in ((a, b), (b, a)):
                d = equiv[x][lang[y]]
                d[y] = max(conf, d.get(y, 0))
    ants = {}
    for src, dst, conf in db.execute("SELECT src, dst, confidence FROM relation WHERE type = 'antonym' AND method = 'source'"):
        a, b = _lex(src), _lex(dst)
        if a in lang and b in lang and a != b and lang[a] == lang[b]:
            k = tuple(sorted((a, b)))
            ants[k] = max(conf, ants.get(k, 0))
    existing = {tuple(sorted((_lex(s), _lex(d)))) for s, d in db.execute("SELECT src, dst FROM relation WHERE type = 'antonym'")}
    out = {}
    for (a, b), ac in ants.items():
        for L in TARGETS.get(lang[a], ()):
            ta, tb = equiv.get(a, {}).get(L, {}), equiv.get(b, {}).get(L, {})
            if not ta or not tb:
                continue
            spread = math.sqrt(len(ta) * len(tb))
            for a2, c1 in ta.items():
                for b2, c2 in tb.items():
                    if a2 == b2:
                        continue
                    key = tuple(sorted((a2, b2)))
                    conf = ac * c1 * c2 / spread
                    if conf >= MIN_OUT and key not in existing and conf > out.get(key, 0):
                        out[key] = conf
    for (x, y), conf in out.items():
        sink.add("relation", src=x, dst=y, type="antonym", method="projected", confidence=round(conf, 2),
                 sources=["projected"])
    sink.flush()
    stats["antonym_projected"] = len(out)
    return out
