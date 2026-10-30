"""mappings/*.tsv 로더 + 원본 값을 공통 체계로 옮기는 함수(§4.2–4.5)."""
from functools import lru_cache

from anikan.common import MAPPINGS, read_tsv

# 활용 부류로 그대로 보존하는 JMdict 엔티티 접두
INFL_PREFIX = ("v5", "v1", "v2", "v4", "vs", "vk", "vz", "vn", "vr", "adj-i", "adj-ix", "adj-ku", "adj-shiku", "adj-nari", "adj-t")


@lru_cache(None)
def pos_map():
    m = {}
    for row in read_tsv(MAPPINGS / "pos.tsv"):
        m[(row[0], row[1])] = row[2] if len(row) > 2 else ""
    return m


@lru_cache(None)
def register_map():
    m = {}
    for row in read_tsv(MAPPINGS / "register.tsv"):
        m[(row[0], row[1])] = row[2]
    return m


@lru_cache(None)
def domain_map():
    return {row[0]: row[1] for row in read_tsv(MAPPINGS / "domain.tsv")}


@lru_cache(None)
def region_map():
    return {(row[0], row[1]): row[2] for row in read_tsv(MAPPINGS / "region.tsv")}


def map_pos(source, raw):
    """원본 품사 하나 → 공통 품사. v5k/v1/vs 같은 JMdict 동사는 모두 verb."""
    if source == "jmdict" and raw.startswith(("v5", "v1", "v2", "v4", "vk", "vz", "vn", "vr")) and raw != "vi" and raw != "vt":
        return "verb"
    if source == "jmdict" and raw.startswith("vs"):
        return "verb"
    return pos_map().get((source, raw))


def jmdict_pos(pos_list):
    """JMdict 한 뜻의 pos 엔티티들 → (공통 품사, 활용 부류).
    명사+する(n, vs)는 noun으로 두고 활용 부류에 vs를 남긴다."""
    common = None
    infl = None
    for p in pos_list:
        if infl is None and p.startswith(INFL_PREFIX):
            infl = p
        c = map_pos("jmdict", p)
        if c and common is None:
            common = c
    return common, infl


REGISTER_PRIORITY = ["honorific", "humble", "polite", "formal", "informal", "slang", "vulgar", "derogatory",
                     "euphemistic", "humorous", "literary", "archaic", "dated", "childish", "feminine", "masculine",
                     "sensitive", "rare"]


def pick_register(values):
    vs = set(values)
    for r in REGISTER_PRIORITY:
        if r in vs:
            return r
    return None


def jmdict_level(entry_pri):
    """JMdict 우선순위 태그 → (level dict, 정렬 점수 0–100)."""
    nf = None
    flags = []
    for p in entry_pri:
        if p.startswith("nf"):
            nf = int(p[2:]) if nf is None else min(nf, int(p[2:]))
        else:
            flags.append(p)
    lv = {}
    if nf:
        lv["nf"] = nf
    if flags:
        lv["pri"] = sorted(set(flags))
    score = 0
    if nf:
        score = (49 - nf) * 2
    elif any(f.endswith("1") for f in flags):
        score = 60
    elif flags:
        score = 30
    if flags:
        lv["common"] = True
    return (lv or None), score
