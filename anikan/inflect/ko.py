"""한국어 활용 생성기(자체 구현). 높임 `-(으)시-`와 합쇼체(-ㅂ니다/습니다)를 만든다.
불규칙 부류(ㅂ·ㄷ·ㅅ·ㅎ·ㄹ)는 이미 알려진 활용형(기초사전 활용 예·kaikki 활용표)에서 판별한다(§4.2)."""

S_BASE, L_COUNT, V_COUNT, T_COUNT = 0xAC00, 19, 21, 28
CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
JUNG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
JONG = ["", "ㄱ", "ㄲ", "ㄳ", "ㄴ", "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ", "ㄻ", "ㄼ", "ㄽ", "ㄾ", "ㄿ", "ㅀ", "ㅁ", "ㅂ", "ㅄ", "ㅅ",
        "ㅆ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"]


def is_syl(c):
    return "가" <= c <= "힣"


def decompose(c):
    n = ord(c) - S_BASE
    return CHO[n // (V_COUNT * T_COUNT)], JUNG[(n % (V_COUNT * T_COUNT)) // T_COUNT], JONG[n % T_COUNT]


def compose(cho, jung, jong=""):
    return chr(S_BASE + (CHO.index(cho) * V_COUNT + JUNG.index(jung)) * T_COUNT + JONG.index(jong))


def final(c):
    return decompose(c)[2] if is_syl(c) else ""


def with_final(c, jong):
    cho, jung, _ = decompose(c)
    return compose(cho, jung, jong)


def classify(lemma, known_forms=()):
    """사전형(-다) → 활용 부류. known_forms는 같은 표제어의 알려진 활용형들."""
    if not lemma.endswith("다") or len(lemma) < 2 or not is_syl(lemma[-2]):
        return None
    stem = lemma[:-1]
    last = stem[-1]
    fin = final(last)
    base = stem[:-1] + with_final(last, "")
    known = [f for f in known_forms if f]

    def has(prefixes):
        return any(f.startswith(p) for f in known for p in prefixes)

    if fin == "ㅂ" and has([base + v for v in "우와워"]):
        return "ko-b-irr"
    if fin == "ㄷ" and has([stem[:-1] + with_final(last, "ㄹ")]):
        return "ko-d-irr"
    if fin == "ㅅ" and has([base + v for v in "어으아이"]) and not has([stem + v for v in "어으아이"]):
        return "ko-s-irr"
    if fin == "ㅎ" and known and not has([stem + v for v in "아어으"]) and has([base]):
        return "ko-h-irr"
    if fin == "ㄹ":
        return "ko-l-drop"
    return "ko-regular"


def honorific_stem(lemma, cls):
    """사전형 → 높임 어간(…시). `가다 → 가시`, `먹다 → 먹으시`, `살다 → 사시`, `돕다 → 도우시`."""
    stem = lemma[:-1]
    last, fin = stem[-1], final(stem[-1])
    head = stem[:-1]
    if cls == "ko-b-irr" and fin == "ㅂ":
        return head + with_final(last, "") + "우시"
    if cls == "ko-d-irr" and fin == "ㄷ":
        return head + with_final(last, "ㄹ") + "으시"
    if cls == "ko-s-irr" and fin == "ㅅ":
        return head + with_final(last, "") + "으시"
    if cls == "ko-h-irr" and fin == "ㅎ":
        # 그렇다 → 그러시, 어떻다 → 어떠시 (ㅎ 탈락 + 모음 교체는 부류마다 달라 가장 흔한 -렇-/-떻-만 다룬다)
        c, j, _ = decompose(last)
        if last in "렇떻":
            return head + compose(c, "ㅓ", "") + "시"
        return None
    if fin == "":
        return stem + "시"
    if fin == "ㄹ":
        return head + with_final(last, "") + "시"
    return stem + "으시"


def honorific_forms(lemma, cls):
    """높임 활용형 → [(표면형, 자질)]"""
    hs = honorific_stem(lemma, cls)
    if not hs:
        return []
    h = hs[:-1]                     # '시' 앞까지
    f = {"honorific": True}
    out = [
        (h + "세요", {**f, "politeness": "polite", "tense": "present", "speech_level": "haeyo"}),
        (h + "십니다", {**f, "politeness": "formal", "tense": "present", "speech_level": "hapsyo"}),
        (h + "십니까", {**f, "politeness": "formal", "tense": "present", "mood": "interrogative"}),
        (h + "십시오", {**f, "politeness": "formal", "mood": "imperative"}),
        (h + "셔", {**f, "tense": "present", "speech_level": "haeche"}),
        (h + "셔요", {**f, "politeness": "polite", "tense": "present"}),
        (h + "셨어요", {**f, "politeness": "polite", "tense": "past", "speech_level": "haeyo"}),
        (h + "셨습니다", {**f, "politeness": "formal", "tense": "past", "speech_level": "hapsyo"}),
        (h + "셨습니까", {**f, "politeness": "formal", "tense": "past", "mood": "interrogative"}),
        (h + "셨다", {**f, "tense": "past"}),
        (h + "셨어", {**f, "tense": "past", "speech_level": "haeche"}),
        (h + "셔서", {**f, "connective": "reason"}),
        (hs + "고", {**f, "connective": "and"}),
        (hs + "면", {**f, "connective": "if"}),
        (hs + "니", {**f, "connective": "because"}),
        (hs + "지만", {**f, "connective": "but"}),
        (hs + "는", {**f, "modifier": "present"}),
        (h + "신", {**f, "modifier": "past"}),
        (h + "실", {**f, "modifier": "future"}),
    ]
    return out


def formal_present(lemma):
    """합쇼체 현재(-ㅂ니다/-습니다). 활용 생성 정확도 검증용 + 색인 보충."""
    stem = lemma[:-1]
    last, fin = stem[-1], final(stem[-1])
    if fin == "":
        return stem[:-1] + with_final(last, "ㅂ") + "니다"
    if fin == "ㄹ":
        return stem[:-1] + with_final(last, "ㅂ") + "니다"
    return stem + "습니다"
