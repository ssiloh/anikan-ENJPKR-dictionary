"""원본 받기: python -m anikan.fetch [jmdict wordnet ejdict kaikki]  (krdict는 raw/krdict에 zip을 둔다)"""
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "raw"


def get(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return
    with urllib.request.urlopen(url) as r, open(dest, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)


def main(which):
    if "jmdict" in which:
        get("https://www.edrdg.org/pub/Nihongo/JMdict.gz", RAW / "jmdict/JMdict.gz")
    if "wordnet" in which:
        get("https://wordnetcode.princeton.edu/3.0/WNdb-3.0.tar.gz", RAW / "wordnet/WNdb-3.0.tar.gz")
        get("https://wordnetcode.princeton.edu/3.0/WordNet-3.0.tar.gz", RAW / "wordnet/WordNet-3.0.tar.gz")
    if "ejdict" in which and not (RAW / "ejdict/repo").exists():
        subprocess.run(["git", "clone", "-q", "https://github.com/kujirahand/EJDict.git", str(RAW / "ejdict/repo")], check=True)
    if "kaikki" in which:
        get("https://kaikki.org/dictionary/Japanese/kaikki.org-dictionary-Japanese.jsonl", RAW / "kaikki/ja.jsonl")
        get("https://kaikki.org/dictionary/Korean/kaikki.org-dictionary-Korean.jsonl", RAW / "kaikki/ko.jsonl")
        if not (RAW / "kaikki/en.filtered.jsonl").exists():
            from anikan.fetch import kaikki_en
            kaikki_en.main(str(RAW / "kaikki/en.filtered.jsonl"))


if __name__ == "__main__":
    main(sys.argv[1:] or ["jmdict", "wordnet", "ejdict", "kaikki"])
