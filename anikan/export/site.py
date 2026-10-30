"""웹앱 조립: web/ 의 정적 파일 + 출처 문서 + 검색 열쇠용 구자체 표를 out/site/ 에 놓는다(데이터는 anikan.export.slim 이 out/site/data 에 만든다).
python -m anikan.export.site [--out out/site]"""
import argparse
import json
import shutil
from pathlib import Path

from anikan.common import OUT, ROOT, kyujitai_map

WEB_FILES = ("index.html", "style.css", "app.js", "keys.js")


def build(out_dir):
    out_dir = Path(out_dir)
    (out_dir / "data").mkdir(parents=True, exist_ok=True)
    for name in WEB_FILES:
        shutil.copy2(ROOT / "web" / name, out_dir / name)
    shutil.copy2(ROOT / "ATTRIBUTION.md", out_dir / "ATTRIBUTION.md")
    (out_dir / "data" / "kyujitai.json").write_text(json.dumps(kyujitai_map(), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return out_dir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT / "site"))
    a = ap.parse_args()
    d = build(a.out)
    has_data = (d / "data" / "manifest.json").exists()
    print(f"site → {d}" + ("" if has_data else "  (data/manifest.json 없음: python -m anikan.export.slim 먼저)"))


if __name__ == "__main__":
    main()
