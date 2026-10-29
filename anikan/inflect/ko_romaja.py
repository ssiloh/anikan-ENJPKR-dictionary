"""국어의 로마자 표기법(Revised Romanization) 규칙 변환(자체 구현). 연음·비음화·유음화·격음화·구개음화는 반영하고
된소리되기는 적지 않는다(학교 → hakgyo)."""
from anikan.inflect.ko import CHO, JONG, JUNG, compose, decompose, is_syl

CHO_R = {"ㄱ": "g", "ㄲ": "kk", "ㄴ": "n", "ㄷ": "d", "ㄸ": "tt", "ㄹ": "r", "ㅁ": "m", "ㅂ": "b", "ㅃ": "pp", "ㅅ": "s",
         "ㅆ": "ss", "ㅇ": "", "ㅈ": "j", "ㅉ": "jj", "ㅊ": "ch", "ㅋ": "k", "ㅌ": "t", "ㅍ": "p", "ㅎ": "h"}
JUNG_R = {"ㅏ": "a", "ㅐ": "ae", "ㅑ": "ya", "ㅒ": "yae", "ㅓ": "eo", "ㅔ": "e", "ㅕ": "yeo", "ㅖ": "ye", "ㅗ": "o",
          "ㅘ": "wa", "ㅙ": "wae", "ㅚ": "oe", "ㅛ": "yo", "ㅜ": "u", "ㅝ": "wo", "ㅞ": "we", "ㅟ": "wi", "ㅠ": "yu",
          "ㅡ": "eu", "ㅢ": "ui", "ㅣ": "i"}
JONG_R = {"": "", "ㄱ": "k", "ㄴ": "n", "ㄷ": "t", "ㄹ": "l", "ㅁ": "m", "ㅂ": "p", "ㅇ": "ng"}
# 겹받침: (앞 소리, 뒤 소리)
DOUBLE = {"ㄳ": ("ㄱ", "ㅅ"), "ㄵ": ("ㄴ", "ㅈ"), "ㄶ": ("ㄴ", "ㅎ"), "ㄺ": ("ㄹ", "ㄱ"), "ㄻ": ("ㄹ", "ㅁ"), "ㄼ": ("ㄹ", "ㅂ"),
          "ㄽ": ("ㄹ", "ㅅ"), "ㄾ": ("ㄹ", "ㅌ"), "ㄿ": ("ㄹ", "ㅍ"), "ㅀ": ("ㄹ", "ㅎ"), "ㅄ": ("ㅂ", "ㅅ")}
NEUTRAL = {"ㄲ": "ㄱ", "ㅋ": "ㄱ", "ㅅ": "ㄷ", "ㅆ": "ㄷ", "ㅈ": "ㄷ", "ㅊ": "ㄷ", "ㅌ": "ㄷ", "ㅍ": "ㅂ"}
ASPIRATE = {"ㄱ": "ㅋ", "ㄷ": "ㅌ", "ㅂ": "ㅍ", "ㅈ": "ㅊ"}
REDUCE = {"ㄳ": "ㄱ", "ㄵ": "ㄴ", "ㄶ": "ㄴ", "ㄺ": "ㄱ", "ㄻ": "ㅁ", "ㄼ": "ㄹ", "ㄽ": "ㄹ", "ㄾ": "ㄹ", "ㄿ": "ㅂ", "ㅀ": "ㄹ",
          "ㅄ": "ㅂ"}
NASAL = {"ㄱ": "ㅇ", "ㄷ": "ㄴ", "ㅂ": "ㅁ"}


def _syl_list(text):
    return [list(decompose(ch)) if is_syl(ch) else ch for ch in text]


def _apply_rules(syls):
    for i in range(len(syls) - 1):
        a, b = syls[i], syls[i + 1]
        if not (isinstance(a, list) and isinstance(b, list)):
            continue
        if a[2] in DOUBLE:
            first, second = DOUBLE[a[2]]
            if b[0] == "ㅇ":                       # 값이 → 갑시, 많이 → 마니
                if second == "ㅎ":
                    a[2], b[0] = "", first
                else:
                    a[2], b[0] = first, second
                continue
            if second == "ㅎ" and b[0] in ASPIRATE:  # 않고 → 안코
                a[2], b[0] = first, ASPIRATE[b[0]]
                continue
            a[2] = "ㄹ" if (a[2] == "ㄺ" and b[0] == "ㄱ") else REDUCE[a[2]]
        if a[2] == "ㅎ":                           # ㅎ 받침: 좋다 → 조타, 좋은 → 조은
            if b[0] in ASPIRATE:
                a[2], b[0] = "", ASPIRATE[b[0]]
            elif b[0] == "ㄴ":
                a[2] = "ㄴ"
            else:
                a[2] = ""
            continue
        if a[2] and a[2] != "ㅇ" and b[0] == "ㅇ":  # 연음 + 구개음화
            moved = a[2]
            if moved in ("ㄷ", "ㅌ") and b[1] == "ㅣ":
                moved = "ㅈ" if moved == "ㄷ" else "ㅊ"
            a[2], b[0] = "", moved
            continue
        a[2] = NEUTRAL.get(a[2], a[2])
        if b[0] == "ㅎ" and a[2] in ASPIRATE:        # 못해 → 모태, 입학 → 이팍
            a[2], b[0] = "", ASPIRATE[a[2]]
        elif a[2] in NASAL and b[0] in ("ㄴ", "ㅁ"):
            a[2] = NASAL[a[2]]
        elif a[2] in NASAL and b[0] == "ㄹ":        # 독립 → 동닙
            a[2], b[0] = NASAL[a[2]], "ㄴ"
        elif a[2] in ("ㅁ", "ㅇ") and b[0] == "ㄹ":  # 심리 → 심니
            b[0] = "ㄴ"
        elif a[2] == "ㄴ" and b[0] == "ㄹ":         # 신라 → 실라
            a[2] = "ㄹ"
        elif a[2] == "ㄹ" and b[0] == "ㄴ":         # 칼날 → 칼랄
            b[0] = "ㄹ"
    for s in syls:                                   # 어말
        if isinstance(s, list):
            s[2] = REDUCE.get(s[2], s[2])
            s[2] = NEUTRAL.get(s[2], s[2])
    return syls


def romanize(text):
    out = []
    prev_l = False
    for s in _apply_rules(_syl_list(text)):
        if isinstance(s, list):
            c, v, j = s
            head = "l" if (c == "ㄹ" and prev_l) else CHO_R.get(c, "")     # 받침 ㄹ 뒤의 ㄹ은 ll
            out.append(head + JUNG_R.get(v, "") + JONG_R.get(j, ""))
            prev_l = j == "ㄹ"
        else:
            out.append(s)
            prev_l = False
    return "".join(out).replace("-", "").replace(" ", "")
