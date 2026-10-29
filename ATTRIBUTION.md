# ATTRIBUTION

이 리포의 결과 데이터는 아래 원본들을 가공한 것이다. 원본의 저작권은 각 저작자에게 있다.
결과 데이터의 각 행은 `sources` 열에 실제로 쓰인 원본을 적는다.

## JMdict / EDRDG

이 데이터는 [JMdict](https://www.edrdg.org/jmdict/j_jmdict.html) 파일을 사용한다. 이 파일은
[EDRDG](https://www.edrdg.org/)(Electronic Dictionary Research and Development Group)의 자산이며,
[EDRDG 라이선스](https://www.edrdg.org/edrdg/licence.html)와 CC BY-SA 4.0 조건으로 사용한다
(`LICENSES/EDRDG-licence.html`).

> This publication has included material from the JMdict (EDICT, etc.) dictionary files in accordance with the
> licence provisions of the Electronic Dictionaries Research Group. See https://www.edrdg.org/

- 이 데이터를 화면으로 보여 주는 사전·앱은 **화면마다(또는 About·Sources 화면에) 위 출처 표시**를 해야 한다. 시작 화면만으로는 부족하다.
- JMdict 자료에 저작권을 주장하지 않는다.

## 한국어기초사전 (국립국어원)

[한국어기초사전](https://krdict.korean.go.kr)의 내려받기 자료(2026-10-19판, JSON)를 사용한다.
라이선스 CC BY-SA 2.0 KR ([저작권 정책](https://krdict.korean.go.kr/kor/kboardPolicy/copyRightTermsInfo)).
저작자: 국립국어원. 이 리포는 자료를 가공(표제어·뜻·대역어를 공통 구조로 변환, 연결 추가)했으며 변경한 자료는 동일 조건(CC BY-SA)으로 배포한다.

## Wiktionary / kaikki.org

[kaikki.org](https://kaikki.org)가 [wiktextract](https://github.com/tatuylonen/wiktextract)로 영어 Wiktionary에서 추출한 자료를 사용한다
(일본어·한국어 2026-10-25판, 영어는 일본어·한국어 번역이 달린 항목만).
Wiktionary 본문은 CC BY-SA 4.0 및 GFDL. 학술적으로 쓸 때는 Tatu Ylonen, *Wiktextract: Wiktionary as Machine-readable Structured Data*, LREC 2022 인용을 요청한다.

## EJDict-hand

[EJDict-hand](https://github.com/kujirahand/EJDict) (kujirahand, 커밋 `2dd9e71`). CC0 1.0 (`LICENSES/EJDict-hand-CC0-1.0.txt`). 의무는 없으나 크레딧을 적는다.

## Princeton WordNet 3.0

WordNet 3.0 Copyright 2006 by Princeton University. All rights reserved.
전체 라이선스와 면책 문구는 `LICENSES/WordNet-3.0.txt`에 원문 그대로 있으며, 이 데이터의 모든 사본·수정본에 포함해야 한다.
Princeton University 이름을 광고·홍보에 쓰지 않는다.

## 이 리포가 직접 만든 것

- `mappings/honorific_core.tsv` 핵심 경어 대응표, `mappings/*.tsv` 대응표: 이 리포가 작성, 결과 데이터와 같은 CC BY-SA 4.0.
- 활용·경어 생성 규칙(`anikan/inflect/`)은 자체 구현이며 다른 프로젝트의 활용 규칙을 복사하지 않았다. 코드는 MIT.

## 라이선스

- 결과 데이터: **CC BY-SA 4.0** (`LICENSES/CC-BY-SA-4.0.txt`)
- 코드: **MIT** (`LICENSE`)
