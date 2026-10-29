"""일본어 활용·경어 생성기(자체 구현). JMdict 활용 부류(v1, v5*, vs, vk)를 입력으로 쓴다."""
import re

U_TO_I = {"う": "い", "く": "き", "ぐ": "ぎ", "す": "し", "つ": "ち", "ぬ": "に", "ぶ": "び", "む": "み", "る": "り"}
U_TO_A = {"う": "わ", "く": "か", "ぐ": "が", "す": "さ", "つ": "た", "ぬ": "な", "ぶ": "ば", "む": "ま", "る": "ら"}
KANJI = re.compile(r"[一-鿿々]")
KANA_ONLY = re.compile(r"^[぀-ヿー]+$")


def base_class(infl):
    """JMdict 활용 부류 → v1 | v5 | vs | vk | None (생성 대상 밖)."""
    if infl in ("v1", "v1-s"):
        return "v1"
    if infl and infl.startswith("v5") and infl not in ("v5aru", "v5r-i"):
        return "v5"
    if infl in ("vs", "vs-i", "vs-s", "vs-c"):
        return "vs"
    if infl == "vk":
        return "vk"
    return None


def stem_forms(lemma, infl):
    """(연용형 어간, 부정 어간, 어미 u) — 생성 불가면 None"""
    c = base_class(infl)
    if c == "v1" and lemma.endswith("る") and len(lemma) >= 2:
        return lemma[:-1], lemma[:-1], "る"
    if c == "v5" and lemma[-1] in U_TO_I:
        u = lemma[-1]
        return lemma[:-1] + U_TO_I[u], lemma[:-1] + U_TO_A[u], u
    if c == "vk" and lemma.endswith(("来る", "くる")):
        return lemma[:-2] + ("来" if lemma.endswith("来る") else "き"), lemma[:-2] + ("来" if lemma.endswith("来る") else "こ"), "る"
    return None


def te_ta(lemma, infl):
    """て형·た형. 5단 동사의 음편, 行く 예외."""
    c = base_class(infl)
    if c == "v1":
        s = lemma[:-1]
        return s + "て", s + "た"
    if c == "vk":
        s = lemma[:-2] + ("来" if lemma.endswith("来る") else "き")
        return s + "て", s + "た"
    if c == "v5":
        u, s = lemma[-1], lemma[:-1]
        if infl == "v5k-s":          # 行く → 行って
            return s + "って", s + "った"
        if infl == "v5u-s":          # 問う → 問うて
            return s + "うて", s + "うた"
        table = {"う": "って", "つ": "って", "る": "って", "く": "いて", "ぐ": "いで", "ぬ": "んで", "ぶ": "んで", "む": "んで", "す": "して"}
        t = table.get(u)
        if not t:
            return None
        ta = t[:-1] + ("だ" if t.endswith("で") else "た")
        return s + t, s + ta
    return None


def polite_forms(lemma, infl):
    """ます형 계열 + 부정·과거·て·た. [(표면형, 자질)]"""
    out = []
    c = base_class(infl)
    if c == "vs":
        noun = lemma[:-2] if lemma.endswith("する") else lemma
        if not noun:
            return []
        s = noun + "し"
        out += [(s + "ます", {"politeness": "polite", "tense": "present"}), (s + "ません", {"politeness": "polite", "polarity": "neg"}),
                (s + "ました", {"politeness": "polite", "tense": "past"}),
                (noun + "して", {"conjunctive": True}), (noun + "した", {"tense": "past"}), (noun + "しない", {"polarity": "neg"})]
        return out
    sf = stem_forms(lemma, infl)
    if not sf:
        return []
    cont, neg, u = sf
    out += [(cont + "ます", {"politeness": "polite", "tense": "present"}),
            (cont + "ません", {"politeness": "polite", "polarity": "neg"}),
            (cont + "ました", {"politeness": "polite", "tense": "past"}),
            (cont + "ませんでした", {"politeness": "polite", "tense": "past", "polarity": "neg"}),
            (cont + "ましょう", {"politeness": "polite", "mood": "volitional"}),
            (neg + "ない", {"polarity": "neg"})]
    tt = te_ta(lemma, infl)
    if tt:
        out += [(tt[0], {"conjunctive": True}), (tt[1], {"tense": "past"})]
    return out


def keigo_forms(lemma, infl):
    """尊敬 `お〜になる`, 謙譲 `お〜する`. vs 한어명사는 `ご〜`. [(표면형, 종류, 자질)]  종류 = honorific | humble"""
    c = base_class(infl)
    out = []
    if c == "vs":
        noun = lemma[:-2] if lemma.endswith("する") else lemma
        if not noun or not KANJI.search(noun):
            return []
        p = "ご" if all(KANJI.match(ch) for ch in noun) else "お"
        for suf, kind in (("になる", "honorific"), ("になります", "honorific"), ("になりました", "honorific"), ("になった", "honorific"),
                          ("なさる", "honorific"), ("なさいます", "honorific"),
                          ("する", "humble"), ("します", "humble"), ("しました", "humble"), ("いたす", "humble"), ("いたします", "humble")):
            out.append((p + noun + suf, kind, {}))
        return out
    if c not in ("v1", "v5"):
        return []
    sf = stem_forms(lemma, infl)
    if not sf:
        return []
    cont = sf[0]
    # 한 글자 어간(見る・着る・居る・寝る …)은 お〜になる 꼴을 만들지 않는다
    if len(cont) < 2 or (c == "v1" and len(cont) == 1):
        return []
    if KANA_ONLY.match(lemma) and len(cont) < 3:
        return []
    p = "お"
    for suf, kind in (("になる", "honorific"), ("になります", "honorific"), ("になりました", "honorific"), ("になった", "honorific"),
                      ("になって", "honorific"), ("ください", "honorific"),
                      ("する", "humble"), ("します", "humble"), ("しました", "humble"), ("いたす", "humble"), ("いたします", "humble")):
        out.append((p + cont + suf, kind, {}))
    return out
