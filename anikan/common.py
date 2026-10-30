"""공통 도우미: 경로, JSONL 입출력, 문자 정규화(§4.1)."""
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
WORK = ROOT / "work"
OUT = ROOT / "out"
MAPPINGS = ROOT / "mappings"


def dumps(o):
    return json.dumps(o, ensure_ascii=False, separators=(",", ":"))


class JsonlWriter:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.f = open(path, "w", encoding="utf-8")
        self.n = 0

    def write(self, o):
        self.f.write(dumps(o) + "\n")
        self.n += 1

    def close(self):
        self.f.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def read_tsv(path):
    """# 주석·빈 줄을 건너뛰고 탭으로 나눈 행을 돌려준다."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line and not line.startswith("#"):
                yield line.split("\t")


# --- §4.1 문자·표기 ---------------------------------------------------------
_CTRL = re.compile(r"[\u0000-\u0008\u000b-\u001f\u007f]")
_STRIP = re.compile(r"[\s・\-\^·･]+")
_PLACEHOLDERS = {"대응 어휘 없음", "no equivalent", "対訳語無し", "対訳語なし", ""}


def nfc(s):
    return _CTRL.sub("", unicodedata.normalize("NFC", s or ""))


def kata_to_hira(s):
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


_KYUJITAI = None


def kyujitai_map():
    global _KYUJITAI
    if _KYUJITAI is None:
        _KYUJITAI = {}
        p = MAPPINGS / "kyujitai.tsv"
        if p.exists():
            for row in read_tsv(p):
                if len(row) >= 2:
                    _KYUJITAI[row[0]] = row[1]
    return _KYUJITAI


def to_shinjitai(s):
    m = kyujitai_map()
    return "".join(m.get(c, c) for c in s)


def search_key(s, lang=None):
    """form.key: NFKC + 소문자 + 공백·・·-·^ 제거. 일본어는 가타카나→히라가나, 구자체→신자체."""
    s = unicodedata.normalize("NFKC", nfc(s)).lower()
    s = _STRIP.sub("", s)
    if lang == "ko":
        s = s.replace("ː", "")   # 발음의 장음 표기
    if lang == "ja":
        s = to_shinjitai(kata_to_hira(s))
    return s


def hanzi_norm(s):
    """한자 비교 열쇠: 구자체·번체를 신자체로 모은다 (일본어 한자 표기 ↔ 한국어 원어)."""
    return to_shinjitai(unicodedata.normalize("NFKC", nfc(s)))


def is_placeholder(s):
    return (s or "").strip() in _PLACEHOLDERS


HANGUL = re.compile(r"[가-힣]")
KANA = re.compile(r"[぀-ヿ]")
