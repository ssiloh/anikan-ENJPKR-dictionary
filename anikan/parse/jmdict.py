"""JMdict(XML) → 중간 JSONL. 엔티티는 이름 그대로(`n`, `v5k`, `hon` …) 보존한다."""
import gzip
import re
import xml.etree.ElementTree as ET

from anikan.common import RAW, WORK, JsonlWriter, nfc

ENT = re.compile(r"&([A-Za-z0-9\-]+);")
STD = {"amp", "lt", "gt", "quot", "apos"}
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


class _Stream:
    """DOCTYPE을 건너뛰고 사용자 엔티티(&n; …)를 이름 문자열로 바꿔 ElementTree에 넘긴다."""

    def __init__(self, path):
        self.f = gzip.open(path, "rt", encoding="utf-8")
        self.in_dtd = False
        self.buf = []
        self.size = 0

    def read(self, n=1 << 16):
        while self.size < n:
            line = self.f.readline()
            if not line:
                break
            if "<!DOCTYPE" in line:
                self.in_dtd = True
            if self.in_dtd:
                if line.strip() == "]>":
                    self.in_dtd = False
                continue
            line = ENT.sub(lambda m: m.group(0) if m.group(1) in STD else m.group(1), line)
            self.buf.append(line)
            self.size += len(line)
        out = "".join(self.buf)
        self.buf, self.size = [], 0
        return out


def _texts(el, tag):
    return [nfc(e.text or "") for e in el.findall(tag)]


def parse(path=None, out_dir=None):
    path = path or RAW / "jmdict/JMdict.gz"
    out_dir = out_dir or WORK
    stream = _Stream(path)
    cnt = {"entry": 0, "keb": 0, "reb": 0, "sense": 0}
    gl = {}
    with JsonlWriter(out_dir / "jmdict.entry.jsonl") as w:
        for _, el in ET.iterparse(stream, events=("end",)):
            if el.tag != "entry":
                continue
            cnt["entry"] += 1
            kele = [{"keb": nfc(k.findtext("keb")), "inf": _texts(k, "ke_inf"), "pri": _texts(k, "ke_pri")}
                    for k in el.findall("k_ele")]
            rele = [{"reb": nfc(r.findtext("reb")), "nokanji": r.find("re_nokanji") is not None,
                     "restr": _texts(r, "re_restr"), "inf": _texts(r, "re_inf"), "pri": _texts(r, "re_pri")}
                    for r in el.findall("r_ele")]
            senses = []
            last_pos = []
            for s in el.findall("sense"):
                pos = _texts(s, "pos") or last_pos
                last_pos = pos
                glosses = {}
                for g in s.findall("gloss"):
                    lang = g.get(XML_LANG, "eng")
                    glosses.setdefault(lang, []).append(nfc(g.text or ""))
                    gl[lang] = gl.get(lang, 0) + 1
                ex = []
                for e in s.findall("example"):
                    d = {"src": e.findtext("ex_srce") or "", "text": "", "tr": ""}
                    for t in e.findall("ex_sent"):
                        lang = t.get(XML_LANG, "")
                        if lang == "jpn":
                            d["text"] = nfc(t.text or "")
                        elif lang == "eng":
                            d["tr"] = nfc(t.text or "")
                    ex.append(d)
                senses.append({
                    "pos": pos, "stagk": _texts(s, "stagk"), "stagr": _texts(s, "stagr"),
                    "xref": _texts(s, "xref"), "ant": _texts(s, "ant"), "field": _texts(s, "field"),
                    "misc": _texts(s, "misc"), "dial": _texts(s, "dial"), "s_inf": _texts(s, "s_inf"),
                    "lsource": [nfc(x.text or "") for x in s.findall("lsource")], "gloss": glosses, "example": ex})
                cnt["sense"] += 1
            cnt["keb"] += len(kele)
            cnt["reb"] += len(rele)
            w.write({"seq": el.findtext("ent_seq"), "k": kele, "r": rele, "s": senses})
            el.clear()
    cnt["gloss"] = gl
    return cnt


if __name__ == "__main__":
    print(parse())
