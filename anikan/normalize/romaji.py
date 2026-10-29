"""가나 → 헵번식 로마자(검색 열쇠용; 장음은 모음을 겹쳐 쓴다: がっこう → gakkou)."""
from anikan.common import kata_to_hira

BASE = {
    "あ": "a", "い": "i", "う": "u", "え": "e", "お": "o", "か": "ka", "き": "ki", "く": "ku", "け": "ke", "こ": "ko",
    "さ": "sa", "し": "shi", "す": "su", "せ": "se", "そ": "so", "た": "ta", "ち": "chi", "つ": "tsu", "て": "te",
    "と": "to", "な": "na", "に": "ni", "ぬ": "nu", "ね": "ne", "の": "no", "は": "ha", "ひ": "hi", "ふ": "fu",
    "へ": "he", "ほ": "ho", "ま": "ma", "み": "mi", "む": "mu", "め": "me", "も": "mo", "や": "ya", "ゆ": "yu",
    "よ": "yo", "ら": "ra", "り": "ri", "る": "ru", "れ": "re", "ろ": "ro", "わ": "wa", "ゐ": "i", "ゑ": "e", "を": "o",
    "ん": "n", "が": "ga", "ぎ": "gi", "ぐ": "gu", "げ": "ge", "ご": "go", "ざ": "za", "じ": "ji", "ず": "zu",
    "ぜ": "ze", "ぞ": "zo", "だ": "da", "ぢ": "ji", "づ": "zu", "で": "de", "ど": "do", "ば": "ba", "び": "bi",
    "ぶ": "bu", "べ": "be", "ぼ": "bo", "ぱ": "pa", "ぴ": "pi", "ぷ": "pu", "ぺ": "pe", "ぽ": "po", "ゔ": "vu",
    "ぁ": "a", "ぃ": "i", "ぅ": "u", "ぇ": "e", "ぉ": "o",
}
SMALL_Y = {"ゃ": "a", "ゅ": "u", "ょ": "o"}
YOON = {  # 이+작은 や행
    "き": "ky", "ぎ": "gy", "し": "sh", "じ": "j", "ち": "ch", "ぢ": "j", "に": "ny", "ひ": "hy", "び": "by",
    "ぴ": "py", "み": "my", "り": "ry",
}
SMALL_V = {"ぁ": "a", "ぃ": "i", "ぅ": "u", "ぇ": "e", "ぉ": "o"}


def to_romaji(kana):
    s = kata_to_hira(kana)
    out = []
    i = 0
    geminate = False
    while i < len(s):
        c = s[i]
        nxt = s[i + 1] if i + 1 < len(s) else ""
        if c == "っ":
            geminate = True
            i += 1
            continue
        if c == "ー":
            if out:
                last = out[-1][-1]
                out.append(last if last in "aiueo" else "")
            i += 1
            continue
        if c in YOON and nxt in SMALL_Y:
            r = YOON[c] + SMALL_Y[nxt] if c not in "しじちぢ" else YOON[c] + SMALL_Y[nxt]
            i += 2
        elif c in BASE and nxt in SMALL_V and c in "ふゔてでうつしちじ":
            r = {"ふ": "f", "ゔ": "v", "て": "t", "で": "d", "う": "w", "つ": "ts", "し": "sh", "ち": "ch", "じ": "j"}[c] + SMALL_V[nxt]
            i += 2
        elif c in BASE:
            r = BASE[c]
            i += 1
            if c == "ん" and nxt and nxt in "あいうえおやゆよ":
                r = "n'"
        else:
            r = c
            i += 1
        if geminate and r and r[0].isalpha():
            r = ("t" + r) if r.startswith("ch") else r[0] + r
        geminate = False
        out.append(r)
    return "".join(out)


MACRON = str.maketrans({"ā": "aa", "ī": "ii", "ū": "uu", "ē": "ee", "ō": "ou", "Ā": "aa", "Ī": "ii", "Ū": "uu", "Ē": "ee", "Ō": "ou"})


def romaji_key(s):
    """사용자가 친 로마자 → 검색 열쇠(장음 부호를 겹모음으로, 공백·아포스트로피 제거)."""
    return s.translate(MACRON).lower().replace("'", "").replace(" ", "").replace("-", "")
