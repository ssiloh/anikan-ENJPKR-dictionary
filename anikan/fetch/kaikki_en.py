"""영어 kaikki(3.4 GB)를 스트림으로 받으면서 일·한 번역이 달린 항목만 남긴다 (≈40 MB)."""
import json
import sys
import urllib.request

URL = "https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl"
KEEP = {"ja", "ko"}


def trim(entry):
    senses = []
    for s in entry.get("senses", []):
        tr = [t for t in s.get("translations", []) if t.get("lang_code") in KEEP]
        if tr:
            senses.append({"glosses": s.get("glosses", []), "tags": s.get("tags", []), "translations": tr})
    top = [t for t in entry.get("translations", []) if t.get("lang_code") in KEEP]
    if not senses and not top:
        return None
    return {"word": entry["word"], "pos": entry.get("pos"), "etymology_number": entry.get("etymology_number"),
            "senses": senses, "translations": top}


def main(out_path, url=URL):
    kept = total = 0
    with urllib.request.urlopen(url) as resp, open(out_path, "w", encoding="utf-8") as out:
        for line in resp:
            total += 1
            e = json.loads(line)
            t = trim(e)
            if t:
                kept += 1
                out.write(json.dumps(t, ensure_ascii=False) + "\n")
            if total % 200000 == 0:
                print(f"{total} lines, kept {kept}", file=sys.stderr, flush=True)
    print(f"done: {total} entries, kept {kept}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1])
