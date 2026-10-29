"""kaikki 일본어의 kyūjitai 표기에서 구자체→신자체 글자 표(mappings/kyujitai.tsv)를 만든다.
한국어 한자(번체)를 일본어 신자체와 맞출 때도 같은 표를 쓴다(구자체 = 번체 계열)."""
from collections import Counter, defaultdict

from anikan.common import MAPPINGS, WORK, read_jsonl


def build():
    votes = defaultdict(Counter)
    for e in read_jsonl(WORK / "kaikki.ja.jsonl"):
        for f in e["forms"]:
            if "kyūjitai" not in f["tags"]:
                continue
            old, new = f["form"], e["word"]
            if len(old) != len(new):
                continue
            for o, n in zip(old, new):
                if o != n and "一" <= o <= "鿿" and "一" <= n <= "鿿":
                    # 단독 한자 항목의 대응이 가장 믿을 만하므로 가중
                    votes[o][n] += 5 if len(new) == 1 else 1
    rows = sorted((o, c.most_common(1)[0][0], sum(c.values())) for o, c in votes.items())
    with open(MAPPINGS / "kyujitai.tsv", "w", encoding="utf-8") as f:
        f.write("# 구자체(번체)\t신자체\t근거 수  — kaikki kyūjitai 표기에서 생성 (anikan.normalize.kyujitai)\n")
        for o, n, c in rows:
            f.write(f"{o}\t{n}\t{c}\n")
    return len(rows)


if __name__ == "__main__":
    print(build(), "pairs")
