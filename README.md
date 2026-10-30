# anikan-ENJPKR-dictionary

한국어 · 일본어 · 영어를 **뜻 단위로** 잇는 오픈 사전 데이터와, 그것을 만드는 코드.
표기·활용형·**경어(존댓말)**로 찾아도 기본형 표제어와 세 언어 대역어가 나온다.

원본: [JMdict](https://www.edrdg.org/jmdict/j_jmdict.html) · [한국어기초사전](https://krdict.korean.go.kr) · [EJDict-hand](https://github.com/kujirahand/EJDict) · [Princeton WordNet 3.0](https://wordnet.princeton.edu/) · [kaikki.org](https://kaikki.org)(Wiktionary)

설계·데이터 구조·연결 방법·라이선스·단계는 [PLAN.md](PLAN.md). 빌드마다 나오는 수치는 `out/stats.md`.

## 만드는 법

```
python -m anikan.fetch                 # JMdict · WordNet · EJDict · kaikki(일·한 + 영어는 번역 달린 것만) 받기
# 한국어기초사전: 누리집 「사전 전체 내려받기」에서 JSON zip을 받아 raw/krdict/json/ 에 푼다 (자동 받기 없음)
python -m anikan.parse.jmdict ; python -m anikan.parse.wordnet ; python -m anikan.parse.ejdict
python -m anikan.parse.kaikki ja ko ; python -m anikan.parse.krdict ; python -m anikan.normalize.kyujitai
python -m anikan.build                 # → out/anikan.sqlite, out/pairs/, out/forms/, out/stats.md  (약 8분)
python -m unittest tests.test_units tests.test_regression
```
파이썬 3.12+ 표준 라이브러리만 쓴다(외부 패키지 없음).

## 써 보기

```
python -m anikan.search 드세요          # 드세요 = 높임·정중 → 들다/드시다 → 먹다 → 食べる · eat
python -m anikan.search 召し上がりました
python -m anikan.search 學校            # 구자체·한자 → 学校 · 학교
```

## 결과물 (`out/`)

| 파일 | 내용 |
|---|---|
| `anikan.sqlite` | lexeme · sense · concept · link · relation · form 전체 |
| `pairs/{ja-ko,ko-ja,en-ja,ja-en,en-ko,ko-en}.jsonl` | 표제어 + 뜻 + 대역어(신뢰도·근거) + 반의어·유의어 + 경어 대응 |
| `pairs/*.tsv` | 신뢰도 0.7 이상, 표제어 ⇥ 읽기 ⇥ 대역어 |
| `forms/{ja,ko}.tsv` | 활용·경어 색인 |
| `stats.md` | 원본별 개수, 방법별 연결 수, 덮는 비율, 활용 생성 정확도 |

결과 데이터는 git에 넣지 않고 GitHub Releases에 올린다. 라이선스: 데이터 **CC BY-SA 4.0**, 코드 **MIT**.
출처 표시와 원본 라이선스는 [ATTRIBUTION.md](ATTRIBUTION.md), `LICENSES/`.
