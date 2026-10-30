// 검색 열쇠와 샤드 해시 — anikan/common.py(search_key)·anikan/normalize/romaji.py(romaji_key)·anikan/export/slim.py(fnv1a)와
// 글자 하나까지 같아야 한다. 어긋나면 검색이 빗나가므로 tests/test_js_parity.py가 파이썬과 대조한다.

// 파이썬 str.isspace()와 같은 공백 집합 (JS의 \s는 U+FEFF를 포함하고 U+0085·U+001C~1F를 빼서 다르다)
const WS = "\\t\\n\\u000b\\f\\r \\u001c-\\u001f\\u0085\\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000";
const CTRL = /[\u0000-\u0008\u000b-\u001f\u007f]/g;
const STRIP = new RegExp(`[${WS}・\\-\\^·･]+`, "g");

let KYU = new Map();

export function setKyujitai(obj) {
  KYU = new Map(Object.entries(obj));
}

export function nfc(s) {
  return (s || "").normalize("NFC").replace(CTRL, "");
}

export function kataToHira(s) {
  let out = "";
  for (const ch of s) {
    const c = ch.codePointAt(0);
    out += c >= 0x30a1 && c <= 0x30f6 ? String.fromCodePoint(c - 0x60) : ch;
  }
  return out;
}

export function toShinjitai(s) {
  let out = "";
  for (const ch of s) out += KYU.get(ch) ?? ch;
  return out;
}

// lang: 'ja' | 'ko' | undefined(영어 등)
export function searchKey(s, lang) {
  s = nfc(s).normalize("NFKC").toLowerCase();
  s = s.replace(STRIP, "");
  if (lang === "ko") s = s.replaceAll("ː", "");
  if (lang === "ja") s = toShinjitai(kataToHira(s));
  return s;
}

const MACRON = { "ā": "aa", "ī": "ii", "ū": "uu", "ē": "ee", "ō": "ou", "Ā": "aa", "Ī": "ii", "Ū": "uu", "Ē": "ee", "Ō": "ou" };

export function romajiKey(s) {
  let out = "";
  for (const ch of s) out += MACRON[ch] ?? ch;
  return out.toLowerCase().replaceAll("'", "").replaceAll(" ", "").replaceAll("-", "");
}

const enc = new TextEncoder();
export function fnv1a(s) {
  let h = 0x811c9dc5;
  for (const b of enc.encode(s)) {
    h ^= b;
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

export const HANGUL = /[가-힣ㄱ-ㆎ]/;
export const KANA = /[぀-ヿ]/;
export const HAN = /[一-鿿]/;

// 입력의 글자 종류로 조회할 (열쇠, 언어) 목록을 정한다. 슬림 색인은 열쇠 문자열로만 찾으므로 중복 열쇠는 하나로 합친다.
export function queryKeys(q) {
  const keys = new Set();
  const add = (k) => k && keys.add(k);
  if (HANGUL.test(q)) {
    add(searchKey(q, "ko"));
  } else if (KANA.test(q)) {
    add(searchKey(q, "ja"));
  } else if (HAN.test(q)) {
    add(searchKey(q, "ja"));      // 일본어 한자(신자체로 맞춘 열쇠)
    add(searchKey(q, "ko"));      // 한국어 한자(번체 그대로)
  } else {
    add(searchKey(q));            // 영어 표제어
    add(romajiKey(q));            // 일본어·한국어 로마자
  }
  return [...keys];
}
