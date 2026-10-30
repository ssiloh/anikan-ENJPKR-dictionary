// anikan 사전 — 정적 JSON 샤드를 브라우저에서 직접 읽는 개인용 사전. 서버 코드 없음.
// 조회 1회 = 색인 샤드(검색어 해시) + 표제어 샤드(표제어 번호). 구조는 data/manifest.json 의 legend.
import { queryKeys, fnv1a, setKyujitai } from "./keys.js";

const DATA = "data/";
const PAGE = 8;                       // 결과 카드는 8개씩 상세를 받아 그린다(표제어마다 샤드가 달라 한꺼번에 받으면 무겁다)
const KIND_RANK = { 0: 0, 1: 1, 2: 2, 3: 2, 4: 3, 5: 4, 6: 5 };
const KIND_LABEL = { 1: "표기 변형", 2: "읽기", 3: "로마자", 4: "활용형", 5: "경어 활용형", 6: "경어 → 기본형" };
const LANG_NAME = { ko: "한국어", ja: "日本語", en: "English" };
const POS = { noun: "명사", verb: "동사", adj: "형용사", "adj-na": "형용동사", adv: "부사", pron: "대명사", num: "수사", det: "관형사",
  particle: "조사", aux: "보조", copula: "지정사", interj: "감탄사", conj: "접속사", affix: "접사", suffix: "접미사", prefix: "접두사",
  phrase: "구", idiom: "관용구", proverb: "속담", grammar: "문법·표현", name: "이름" };
const REG = { honorific: "높임·尊敬", humble: "낮춤·謙譲", polite: "정중", formal: "격식", informal: "구어", literary: "문어", archaic: "고어",
  dated: "예스러운", slang: "속어", vulgar: "비속", derogatory: "비하", euphemistic: "완곡", humorous: "해학", childish: "아동어",
  feminine: "여성어", masculine: "남성어", sensitive: "민감", rare: "드문" };
const FEAT = { honorific: "높임", humble: "겸양", polite: "정중", formal: "격식", informal: "비격식", past: "과거", "non-past": "현재",
  present: "현재", future: "미래", negative: "부정", neg: "부정", imperative: "명령", interrogative: "의문", hortative: "청유",
  conjunctive: "연결", continuative: "연용", volitional: "의지", potential: "가능", infinitive: "연결(어)", sequential: "연결(니)",
  causative: "사역", passive: "수동", conditional: "조건", attributive: "연체", determiner: "관형", stem: "어간", ja: "", ko: "" };
const REL_LABEL = { ant: "반의어", syn: "유의어" };
const EXAMPLES = ["드세요", "召し上がりました", "お書きになる", "먹다", "食べません", "學校", "gakkou", "eat"];

const $ = (s) => document.querySelector(s);
const main = $("#main");
const input = $("#q");
let man = null;

function el(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "text") e.textContent = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) if (kid != null && kid !== false) e.append(kid);
  return e;
}

// ---- 데이터 읽기 (최근 48개 샤드만 메모리에 둔다) ----
const cache = new Map();
function getJson(path) {
  if (cache.has(path)) {
    const p = cache.get(path);
    cache.delete(path);
    cache.set(path, p);
    return p;
  }
  const p = fetch(DATA + path).then((r) => {
    if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
    return r.json();
  });
  p.catch(() => cache.delete(path));
  cache.set(path, p);
  while (cache.size > 48) cache.delete(cache.keys().next().value);
  return p;
}
async function getLex(n) {
  const sh = await getJson(`lex/${n % man.shards.lex}.json`);
  return sh[String(n)] || null;
}
async function init() {
  if (man) return;
  const [m, kyu] = await Promise.all([fetch(DATA + "manifest.json").then((r) => r.json()), fetch(DATA + "kyujitai.json").then((r) => r.json())]);
  setKyujitai(kyu);
  man = m;
}

async function lookup(q) {
  const keys = queryKeys(q);
  const shards = await Promise.all(keys.map((k) => getJson(`idx/${fnv1a(k) % man.shards.idx}.json`)));
  const best = new Map();
  let order = 0;
  keys.forEach((k, i) => {
    for (const [n, kind, feat, via] of shards[i][k] || []) {
      const rank = KIND_RANK[kind];
      const cur = best.get(n);
      if (!cur || rank < cur.rank) best.set(n, { n, kind, feat, via: via || 0, rank, order: order++ });
    }
  });
  return [...best.values()].sort((a, b) => a.rank - b.rank || a.order - b.order);
}

// ---- 표시 도우미 ----
const langOf = (d) => d.i.split(":", 1)[0];
const pct = (c) => Math.round(c * 100) + "%";
function featText(code) {
  if (!code) return "";
  const parts = [];
  for (const f of man.features[code].split(",")) {
    const t = FEAT[f] ?? f;
    if (t && !parts.includes(t)) parts.push(t);
  }
  return parts.join("·");
}
function badge(lang) {
  return el("span", { class: `badge ${lang}`, text: lang.toUpperCase() });
}
function link(n, text, extra = {}) {
  return el("a", { href: `#/w/${n}`, ...extra, text });
}
function levelChip(d) {
  const v = d.v;
  if (!v) return null;
  if (v.krdict) return el("span", { class: "chip", text: v.krdict });
  if (v.common) return el("span", { class: "chip", title: "우선순위 태그가 있는 자주 쓰는 말", text: "자주 쓰임" });
  return null;
}
function tags(d) {
  return [badge(langOf(d)), d.p && el("span", { class: "chip", text: POS[d.p] || d.p }),
    d.g && el("span", { class: `chip ${["honorific", "humble", "polite"].includes(d.g) ? "hon" : ""}`, text: REG[d.g] || d.g }), levelChip(d)];
}
function glossLine(d) {
  const lang = langOf(d);
  const s0 = (d.s || []).slice(0, 2);
  const bits = [];
  for (const s of s0) {
    const e = s.e || {};
    const g = lang === "ja" ? e.en : lang === "ko" ? (e.ja || e.en) : null;
    bits.push((lang === "en" ? s.d : lang === "ko" && s.d ? s.d : (g || []).slice(0, 4).join(", ")) || "");
  }
  return bits.filter(Boolean).join(" / ");
}

// ---- 화면: 결과 카드 ----
async function card(hit) {
  const [d, via] = await Promise.all([getLex(hit.n), hit.via ? getLex(hit.via) : null]);
  if (!d) return null;
  const lang = langOf(d);
  const row2 = [];
  if (hit.kind) {
    const f = featText(hit.feat);
    const label = KIND_LABEL[hit.kind];
    row2.push(el("span", { class: `chip ${hit.kind >= 5 ? "via" : ""}`, text: f ? `${label} · ${f}` : label }));
    if (hit.kind === 6 && via) row2.push(el("span", { class: "chip via" }, "경어 표제어 ", link(hit.via, via.l)));
  }
  const gl = glossLine(d);
  const tr = [];
  for (const lg of ["ko", "ja", "en"]) {
    if (lg === lang || !d.t?.[lg]) continue;
    tr.push(el("div", { class: "tr" }, el("span", { class: "lab", text: LANG_NAME[lg] }),
      d.t[lg].slice(0, 3).map(([n, l, r]) => link(n, r ? `${l} (${r})` : l, { lang: lg }))));
  }
  return el("article", { class: "card" },
    el("h3", {}, link(hit.n, d.l, { lang }), d.r && el("small", { lang, text: d.r })),
    el("div", { class: "row" }, tags(d)), row2.length && el("div", { class: "row" }, row2),
    gl && el("div", { class: "gl", lang: lang === "ko" ? "ko" : undefined, text: gl }), tr);
}

let token = 0;
async function showSearch(q) {
  const my = ++token;
  main.replaceChildren(el("p", { class: "hint", text: "찾는 중…" }));
  let hits;
  try {
    await init();
    hits = await lookup(q);
  } catch (e) {
    return showError(e);
  }
  if (my !== token) return;
  if (!hits.length) {
    main.replaceChildren(el("p", { class: "empty" }, `"${q}" 결과가 없어요. `,
      "활용형·존댓말·한자·로마자도 찾지만 사전에 없는 말이면 나오지 않아요."));
    return;
  }
  const box = el("div");
  const more = el("button", { class: "more", type: "button" });
  let shown = 0;
  const loadMore = async () => {
    more.disabled = true;
    more.textContent = "불러오는 중…";
    const batch = hits.slice(shown, shown + PAGE);
    const cards = await Promise.all(batch.map(card));
    if (my !== token) return;
    box.append(...cards.filter(Boolean));
    shown += batch.length;
    more.disabled = false;
    more.textContent = `더 보기 (${hits.length - shown}개 남음)`;
    if (shown >= hits.length) more.remove();
  };
  more.addEventListener("click", loadMore);
  main.replaceChildren(...[el("p", { class: "hint", text: `${hits.length}개` }), box, hits.length > PAGE && more].filter(Boolean));
  await loadMore();
}

// ---- 화면: 상세 ----
function pill(r, lang) {
  const [n, l, rd, c, methods] = r;
  return el("a", { class: "pill", href: `#/w/${n}`, title: methods ? `근거: ${methods.split("+").join(", ")}` : "" },
    el("span", { lang, text: l }), rd && el("span", { class: "r", text: rd }), c != null && el("span", { class: "c", text: pct(c) }));
}
function senseItem(s, lang) {
  const li = el("li");
  if (s.d) li.append(el("div", { class: "def", lang: lang === "ko" ? "ko" : undefined, text: s.d }));
  for (const [lg, list] of Object.entries(s.e || {})) {
    li.append(el("div", { class: "muted" }, el("span", { text: lg.toUpperCase() + " " }), el("span", { lang: lg, text: list.join("; ") })));
  }
  const chips = [];
  if (s.g) chips.push(el("span", { class: `chip ${["honorific", "humble", "polite"].includes(s.g) ? "hon" : ""}`, text: REG[s.g] || s.g }));
  for (const k of ["domain", "region", "usage"]) for (const v of s.b?.[k] || []) chips.push(el("span", { class: "chip", text: v.replace("region:", "") }));
  if (chips.length) li.append(el("div", { class: "row" }, chips));
  for (const x of s.x || []) {
    li.append(el("div", { class: "ex" }, el("div", { lang, text: x.t }), x.x && el("div", { class: "x", text: x.x })));
  }
  return li;
}
function relSection(d) {
  const q = d.q || {};
  const out = [];
  const group = (title, list) => out.push(el("div", { class: "sec" }, el("h4", { text: title }), list.map((r) => pill(r, langOf(d)))));
  if (q.hon) group("이 말은 아래 말의 높임말(존경)", q.hon);
  if (q.hum) group("이 말은 아래 말의 낮춤말(겸양)", q.hum);
  if (q.pol) group("이 말은 아래 말의 정중한 말", q.pol);
  if (q.hon_of) group("이 말의 높임 표현", q.hon_of);
  if (q.hum_of) group("이 말의 겸양 표현", q.hum_of);
  if (q.pol_of) group("이 말의 정중 표현", q.pol_of);
  for (const k of ["ant", "syn"]) if (q[k]) group(REL_LABEL[k], q[k]);
  return out;
}
async function showLexeme(n) {
  const my = ++token;
  main.replaceChildren(el("p", { class: "hint", text: "불러오는 중…" }));
  let d;
  try {
    await init();
    d = await getLex(n);
  } catch (e) {
    return showError(e);
  }
  if (my !== token) return;
  if (!d) return main.replaceChildren(el("p", { class: "empty", text: "없는 표제어예요." }));
  const lang = langOf(d);
  const detail = el("div", { class: "detail" },
    el("a", { class: "back", href: "javascript:history.back()", text: "← 뒤로" }),
    el("h2", {}, el("span", { lang, text: d.l }), d.r && el("small", { lang, text: d.r }), d.z && el("small", { text: d.z })),
    el("div", { class: "row" }, tags(d)));
  if (d.s?.length) detail.append(el("div", { class: "sec" }, el("h4", { text: "뜻" }), el("ol", { class: "senses" }, d.s.map((s) => senseItem(s, lang)))));
  for (const lg of ["ko", "ja", "en"]) {
    if (lg === lang || !d.t?.[lg]) continue;
    detail.append(el("div", { class: "sec" }, el("h4", { text: `${LANG_NAME[lg]} 대역어` }), d.t[lg].map((r) => pill(r, lg))));
  }
  detail.append(...relSection(d));
  detail.append(el("p", { class: "muted", text: d.i }));
  main.replaceChildren(detail);
  document.title = `${d.l} · anikan`;
}

// ---- 화면: 처음·출처·오류 ----
function showHome() {
  token++;
  main.replaceChildren(el("p", { class: "hint", text: "한국어·일본어·영어를 뜻 단위로 이은 사전이에요. 기본형이 아니어도, 존댓말·경어형이어도 기본형을 찾아줘요." }),
    el("div", { class: "examples" }, EXAMPLES.map((e) => el("a", { href: `#/q/${encodeURIComponent(e)}`, text: e }))));
}
async function showAbout() {
  token++;
  let text = "";
  try {
    text = await fetch("ATTRIBUTION.md").then((r) => (r.ok ? r.text() : ""));
  } catch (e) { /* 아래에서 안내 */ }
  const pre = el("pre", { class: "about" });
  for (const part of (text || "ATTRIBUTION.md 를 읽지 못했어요. 저장소의 ATTRIBUTION.md 를 보세요.").split(/(https?:\/\/[^\s)>]+)/)) {
    pre.append(/^https?:/.test(part) ? el("a", { href: part, text: part, rel: "noopener", target: "_blank" }) : part);
  }
  main.replaceChildren(el("a", { class: "back", href: "#/", text: "← 처음으로" }), pre);
}
function showError(e) {
  console.error(e);
  main.replaceChildren(el("p", { class: "err", text: `데이터를 읽지 못했어요: ${e.message}` }),
    el("p", { class: "hint" }, "file:// 로 열면 브라우저가 파일 읽기를 막아요. 이 폴더에서 `python -m anikan.serve` 로 서버를 띄운 뒤 주소로 접속하세요."));
}

// ---- 라우팅·입력 ----
function route() {
  const h = decodeURIComponent(location.hash.slice(1));
  document.title = "anikan 사전";
  if (h.startsWith("/w/")) return showLexeme(Number(h.slice(3)));
  if (h.startsWith("/q/")) {
    const q = h.slice(3);
    if (input.value !== q) input.value = q;
    return showSearch(q);
  }
  if (h === "/about") return showAbout();
  input.value = "";
  showHome();
}
const goSearch = (q, replace) => {
  const url = q.trim() ? `#/q/${encodeURIComponent(q.trim())}` : "#/";
  if (replace) history.replaceState(null, "", url), route();
  else location.hash = url;
};
let timer = 0;
input.addEventListener("input", (e) => {
  if (e.isComposing) return;
  clearTimeout(timer);
  timer = setTimeout(() => goSearch(input.value, true), 300);
});
input.addEventListener("compositionend", () => {
  clearTimeout(timer);
  timer = setTimeout(() => goSearch(input.value, true), 300);
});
$("#form").addEventListener("submit", (e) => {
  e.preventDefault();
  clearTimeout(timer);
  goSearch(input.value, false);
  input.blur();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "/" && document.activeElement !== input) {
    e.preventDefault();
    input.focus();
    input.select();
  } else if (e.key === "Escape" && document.activeElement === input) {
    input.value = "";
    goSearch("", false);
  }
});
window.addEventListener("hashchange", route);
route();
