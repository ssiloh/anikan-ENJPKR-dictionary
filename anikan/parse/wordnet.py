"""Princeton WordNet 3.0(WNdb) → synset·sense JSONL."""
import re
import tarfile

from anikan.common import RAW, WORK, JsonlWriter

POS = {"noun": "n", "verb": "v", "adj": "a", "adv": "r"}
SS_TYPE = {"n": "n", "v": "v", "a": "a", "s": "a", "r": "r"}


def _lines(tf, name):
    f = tf.extractfile(f"dict/{name}")
    for raw in f:
        line = raw.decode("utf-8")
        if not line.startswith("  "):
            yield line.rstrip("\n")


def parse(path=None, out_dir=None):
    path = path or RAW / "wordnet/WNdb-3.0.tar.gz"
    out_dir = out_dir or WORK
    stats = {"synset": 0, "sense": 0, "antonym_ptr": 0}
    tf = tarfile.open(path)
    lexnames = {}
    # lexfile 이름은 data 줄의 lex_filenum → 이름 (lexnames 표는 WNdb에 없어 고정 표를 쓴다)
    from anikan.parse.wn_lexnames import LEXNAMES
    lexnames = LEXNAMES
    tagcount = {}
    for line in _lines(tf, "index.sense"):
        key, off, rank, cnt = line.split(" ")
        tagcount[key] = int(cnt)
    with JsonlWriter(out_dir / "wordnet.synset.jsonl") as w:
        for pos_name, p in POS.items():
            for line in _lines(tf, f"data.{pos_name}"):
                head, _, gloss = line.partition(" | ")
                t = head.split(" ")
                offset, lexnum, ss, wcnt = t[0], int(t[1]), t[2], int(t[3], 16)
                words, i = [], 4
                for _ in range(wcnt):
                    lemma, lexid = t[i], int(t[i + 1], 16)
                    words.append([lemma, lexid])
                    i += 2
                pcnt = int(t[i]); i += 1
                ptrs = []
                for _ in range(pcnt):
                    sym, off, ppos, st = t[i:i + 4]
                    ptrs.append([sym, off, SS_TYPE.get(ppos, ppos), st])
                    i += 4
                    if sym == "!":
                        stats["antonym_ptr"] += 1
                gloss_text, _, examples = gloss.partition("; \"")
                w.write({"id": f"wn30:{offset}-{SS_TYPE[ss]}", "pos": SS_TYPE[ss], "ss_type": ss, "lexfile": lexnames[lexnum],
                         "words": words, "ptrs": ptrs, "gloss": gloss.strip().rstrip(";").strip()})
                stats["synset"] += 1
                stats["sense"] += len(words)
    # 표제어 → synset(빈도순)
    with JsonlWriter(out_dir / "wordnet.index.jsonl") as w:
        for pos_name, p in POS.items():
            for line in _lines(tf, f"index.{pos_name}"):
                t = line.split(" ")
                lemma, pos, syn_cnt, ptr_cnt = t[0], t[1], int(t[2]), int(t[3])
                rest = t[4:]
                rest = rest[ptr_cnt:]
                sense_cnt, tagged = int(rest[0]), int(rest[1])
                offs = rest[2:2 + syn_cnt]
                w.write({"lemma": lemma.replace("_", " "), "pos": p, "synsets": [f"wn30:{o}-{p}" for o in offs], "tagged": tagged})
    with JsonlWriter(out_dir / "wordnet.sensekey.jsonl") as w:
        for line in _lines(tf, "index.sense"):
            key, off, rank, cnt = line.split(" ")
            w.write({"key": key, "offset": off, "rank": int(rank), "tag_count": int(cnt)})
    stats["tagged_senses"] = sum(1 for c in tagcount.values() if c > 0)
    stats["tag_total"] = sum(tagcount.values())
    return stats


if __name__ == "__main__":
    print(parse())
