// python tests/test_js_parity.py가 호출한다: node tests/js/parity.mjs cases.json kyujitai.json
import fs from "node:fs";
import { searchKey, romajiKey, fnv1a, setKyujitai } from "../../web/keys.js";

const [casesPath, kyuPath] = process.argv.slice(2);
setKyujitai(JSON.parse(fs.readFileSync(kyuPath, "utf-8")));
const cases = JSON.parse(fs.readFileSync(casesPath, "utf-8"));
const bad = [];
for (const c of cases) {
  const got = { ja: searchKey(c.q, "ja"), ko: searchKey(c.q, "ko"), en: searchKey(c.q), romaji: romajiKey(c.q) };
  got.h = fnv1a(got.ja);
  for (const k of Object.keys(got)) {
    if (got[k] !== c[k]) bad.push({ q: c.q, field: k, js: got[k], py: c[k] });
  }
}
console.log(JSON.stringify({ checked: cases.length, mismatches: bad.slice(0, 20), n_bad: bad.length }));
