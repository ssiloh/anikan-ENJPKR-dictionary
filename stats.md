# stats

빌드마다 `python -m anikan.build`가 다시 쓴다.

## 표제어

| 언어 | 원본 | 표제어 |
|---|---|---|
| en | wordnet | 147,306 |
| en | kaikki | 13,749 |
| en | ejdict | 6,565 |
| ja | jmdict | 218,975 |
| ja | kaikki | 21,526 |
| ko | krdict | 56,555 |
| ko | kaikki | 14,783 |

## 연결(link) — 방법별

| kind | method | 줄 수 | 평균 신뢰도 | 0.7 이상 |
|---|---|---|---|---|
| concept | wn_concept | 236,659 | 0.73 | 133,020 |
| translation | jmdict_gloss | 200,959 | 0.90 | 200,959 |
| translation | krdict_equivalent | 178,589 | 0.84 | 143,536 |
| translation | kaikki_translation | 114,518 | 0.71 | 81,905 |
| translation | ejdict | 41,568 | 0.71 | 15,357 |
| translation | kaikki_triangle | 37,366 | 0.71 | 28,151 |
| translation | en_pivot | 31,727 | 0.43 | 313 |
| translation | hanzi_match | 21,198 | 0.68 | 8,133 |

## 관계(relation)

| type | method | 줄 수 |
|---|---|---|
| see_also | source | 88,851 |
| derived | source | 52,064 |
| synonym | source | 48,053 |
| antonym | source | 16,687 |
| abbrev_of | source | 1,212 |
| small_form | source | 1,188 |
| large_form | source | 1,159 |
| antonym | projected | 939 |
| soft_form | source | 611 |
| strong_form | source | 511 |
| honorific_of | definition | 376 |
| honorific_of | source | 281 |
| polite_of | source | 210 |
| humble_of | definition | 118 |
| polite_of | definition | 110 |
| humble_of | source | 71 |
| honorific_of | curated | 38 |
| humble_of | curated | 33 |

## 검색 색인(form)

| 언어 | kind | 줄 수 |
|---|---|---|
| en | lemma | 167,620 |
| ja | inflection | 669,722 |
| ja | honorific_inflection | 391,993 |
| ja | romaji | 287,668 |
| ja | lemma | 249,689 |
| ja | reading | 190,595 |
| ja | variant | 80,644 |
| ja | lexical_honorific | 7,616 |
| ko | inflection | 347,547 |
| ko | honorific_inflection | 281,046 |
| ko | romaji | 72,362 |
| ko | lemma | 71,338 |
| ko | reading | 56,755 |
| ko | hanzi | 44,360 |
| ko | variant | 3,559 |
| ko | lexical_honorific | 1,547 |

## 활용 생성 정확도 (원본 활용형과 겹치는 단어 기준)

| 항목 | 맞음 / 비교 대상 | 비율 |
|---|---|---|
| 한국어 합쇼체 현재(-ㅂ니다/-습니다) | 7,198 / 7,207 | 99.9% |
| 일본어 ます형 | 9,626 / 9,688 | 99.4% |
| 한국어 로마자(국어의 로마자 표기법) — kaikki 표기와 일치 | 32,730 / 33,816 | 96.8% |
| 한국어 높임(-시-) — 실제 높임 활용표가 있는 -시다 표제어만 | 43 / 48 | 89.6% |

한국어 높임 비교 모집단은 23개 표제어뿐이고(kaikki에 `-시다` 활용표가 거의 없음), 틀린 건 어간이 우연히 `-시다`인 일반 동사(꼬시다·마시다·쑤시다·부시다)와의 철자 중복이다.


## 커버리지

- 기초사전 초급 어휘 2,545개 중 일본어 연결(0.7↑)이 있는 것: 2,271 (89.2%)
- JMdict 상용어(우선순위 태그) 30,169개 중 한국어 연결(0.5↑)이 있는 것: 20,606 (68.3%)
- 기초사전 동사·형용사 14,195개 중 높임 활용 색인이 있는 것: 14,112 (99.4%)

## 빌드 수치 (원본 대조)

```json
{
 "jm_sense": 678609,
 "jm_lexeme": 218975,
 "jm_rel_ok": 38148,
 "jm_rel_unresolved": 1,
 "ja_entries": 200030,
 "ja_merged": 79009,
 "ja_skipped_romanization": 32126,
 "ja_inflection_forms": 386098,
 "ja_redirect_entries": 45031,
 "ja_skipped_character": 15007,
 "ja_form_of_entries": 6406,
 "ja_created": 21526,
 "ja_sense": 27451,
 "ja_skipped_syllable": 789,
 "ja_skipped_punct": 36,
 "ja_honorific_gloss": 33,
 "ja_skipped_symbol": 100,
 "ja_rel_ok": 83362,
 "ja_rel_unresolved": 30340,
 "ja_form_of_ok": 66913,
 "ja_form_of_unresolved": 7257,
 "wn_sense": 206978,
 "wn_antonym_rel": 7979,
 "ej_link": 41568,
 "ej_unresolved": 45559,
 "kr_sense": 76833,
 "kr_rel_반대말": 2680,
 "kr_rel_높임말": 79,
 "kr_rel_참고어": 10214,
 "kr_rel_유의어": 13665,
 "kr_rel_큰말": 1159,
 "kr_rel_센말": 511,
 "kr_rel_여린말": 611,
 "kr_rel_준말": 604,
 "kr_rel_본말": 608,
 "kr_rel_작은말": 1188,
 "kr_rel_낮춤말": 15,
 "kr_ja_links": 73929,
 "kr_ja_unlinked": 35053,
 "kr_en_links": 69607,
 "kr_def_hon_ok": 37,
 "kr_def_hon_phrase": 174,
 "kr_def_hon_unresolved": 0,
 "ko_entries": 64457,
 "ko_skipped_character": 10300,
 "ko_created": 14783,
 "ko_sense": 16121,
 "ko_skipped_symbol": 19,
 "ko_merged": 24239,
 "ko_form_of_entries": 14711,
 "ko_skipped_romanization": 8,
 "ko_skipped_syllable": 377,
 "ko_inflection_forms": 292612,
 "ko_skipped_punct": 20,
 "ko_honorific_gloss": 44,
 "ko_rel_ok": 29251,
 "ko_rel_unresolved": 16221,
 "ko_form_of_ok": 12933,
 "ko_form_of_unresolved": 1778,
 "kk_en_lexeme_new": 13749,
 "kk_en_translation_links": 114518,
 "kk_triangle_links": 37366,
 "kk_unlinked": 32613,
 "jm_gloss_links": 200959,
 "hon_curated": 71,
 "hon_curated_verified": 61,
 "hon_curated_review": 17,
 "hon_by_gloss": 508,
 "hanzi_match_ok": 8133,
 "hanzi_match_false_friend": 2156,
 "hanzi_match_unchecked": 10909,
 "en_pivot_links": 31727,
 "wn_concept_links": 236659,
 "antonym_projected": 939,
 "ko_gen_honorific_forms": 281029,
 "ko_gen_formal_forms": 7677,
 "ko_class": {
  "ko-regular": 14091,
  "ko-b-irr": 394,
  "ko-l-drop": 287,
  "ko-s-irr": 32,
  "ko-h-irr": 60,
  "ko-d-irr": 23
 },
 "ko_eval": {
  "formal_n": 7207,
  "formal_hit": 7198,
  "hon_n": 48,
  "hon_hit": 43,
  "hon_pop": 23,
  "hon_covered": 12
 },
 "ja_gen_polite_forms": 290528,
 "ja_gen_keigo_forms": 391985,
 "ja_eval": {
  "polite_n": 9688,
  "polite_hit": 9626
 },
 "ko_romaja_forms": 38455,
 "ko_romaja_eval": {
  "n": 33816,
  "hit": 32730
 },
 "lexical_honorific_forms": 10423,
 "lexical_honorific_pairs": 1132,
 "form_dedup_removed": 263558,
 "pairs": {
  "ja-ko": {
   "entries": 48907,
   "tsv_entries": 43328
  },
  "ko-ja": {
   "entries": 47895,
   "tsv_entries": 45459
  },
  "en-ja": {
   "entries": 66091,
   "tsv_entries": 62665
  },
  "ja-en": {
   "entries": 111371,
   "tsv_entries": 109986
  },
  "en-ko": {
   "entries": 27652,
   "tsv_entries": 27652
  },
  "ko-en": {
   "entries": 43190,
   "tsv_entries": 43190
  }
 },
 "forms_tsv": {
  "ja": 1069331,
  "ko": 630140
 }
}
```
