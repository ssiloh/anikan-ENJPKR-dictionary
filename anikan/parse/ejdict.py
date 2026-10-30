"""EJDict-hand(TSV) → 줄 단위 JSONL. 뜻 안 표시(《話》〈C〉 …)는 labels로 뽑고 원문은 보존."""
import re

from anikan.common import RAW, WORK, JsonlWriter, nfc

MARK = re.compile(r"《([^》]+)》")
COUNT = re.compile(r"〈([CU])〉")
HEAD_KANJI = re.compile(r"『([^』]*)』")


def parse(repo=None, out_dir=None):
    repo = repo or RAW / "ejdict/repo"
    out_dir = out_dir or WORK
    stats = {"lines": 0, "headwords": 0, "marks": {}}
    freq = {}
    for name in ("100", "850", "2000"):
        for p in (repo / "frequency").glob(f"*{name}*"):
            freq[name] = {w.strip().lower() for w in p.read_text(encoding="utf-8").splitlines() if w.strip()}
    with JsonlWriter(out_dir / "ejdict.jsonl") as w:
        for p in sorted((repo / "src").glob("*.txt")):
            for line in p.read_text(encoding="utf-8").splitlines():
                if not line.strip() or "\t" not in line:
                    continue
                head, _, meaning = line.partition("\t")
                heads = [nfc(h.strip()) for h in head.split(",") if h.strip()]
                marks = MARK.findall(meaning)
                for m in marks:
                    stats["marks"][m] = stats["marks"].get(m, 0) + 1
                lists = [k for k, v in freq.items() if any(h.lower() in v for h in heads)]
                w.write({"heads": heads, "meaning": nfc(meaning), "senses": [nfc(x) for x in meaning.split(" / ")],
                         "marks": marks, "count": COUNT.findall(meaning), "lists": lists})
                stats["lines"] += 1
                stats["headwords"] += len(heads)
    return stats


if __name__ == "__main__":
    s = parse()
    s["marks"] = dict(sorted(s["marks"].items(), key=lambda kv: -kv[1])[:12])
    print(s)
