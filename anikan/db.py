"""SQLite 스키마(§3.1)와 일괄 삽입 도우미."""
import sqlite3

from anikan.common import dumps

SCHEMA = """
CREATE TABLE lexeme (
  id TEXT PRIMARY KEY, lang TEXT NOT NULL, lemma TEXT NOT NULL, reading TEXT, hanzi TEXT, hanzi_norm TEXT,
  pos TEXT, infl_class TEXT, register TEXT, level TEXT, score INTEGER DEFAULT 0,
  source TEXT NOT NULL, source_id TEXT NOT NULL, extra TEXT
);
CREATE TABLE sense (
  id TEXT PRIMARY KEY, lexeme_id TEXT NOT NULL, ord INTEGER, definition TEXT, def_lang TEXT, glosses TEXT,
  register TEXT, labels TEXT, examples TEXT, extra TEXT
);
CREATE TABLE concept (id TEXT PRIMARY KEY, pos TEXT, lemmas TEXT, gloss TEXT, lexfile TEXT);
CREATE TABLE link (
  src TEXT NOT NULL, dst TEXT NOT NULL, kind TEXT NOT NULL, method TEXT NOT NULL,
  confidence REAL NOT NULL, evidence TEXT, sources TEXT NOT NULL
);
CREATE TABLE relation (
  src TEXT NOT NULL, dst TEXT NOT NULL, type TEXT NOT NULL, method TEXT NOT NULL,
  confidence REAL NOT NULL, sources TEXT NOT NULL
);
CREATE TABLE form (
  key TEXT NOT NULL, surface TEXT NOT NULL, lang TEXT NOT NULL, lexeme_id TEXT NOT NULL, kind TEXT NOT NULL,
  features TEXT, via TEXT, source TEXT NOT NULL
);
"""

INDEXES = """
CREATE INDEX form_key ON form(key, lang);
CREATE INDEX form_lex ON form(lexeme_id);
CREATE INDEX sense_lex ON sense(lexeme_id);
CREATE INDEX lexeme_lang_lemma ON lexeme(lang, lemma);
CREATE INDEX link_src ON link(src);
CREATE INDEX link_dst ON link(dst);
CREATE INDEX relation_src ON relation(src);
CREATE INDEX relation_dst ON relation(dst);
"""

COLS = {
    "lexeme": ["id", "lang", "lemma", "reading", "hanzi", "hanzi_norm", "pos", "infl_class", "register", "level",
               "score", "source", "source_id", "extra"],
    "sense": ["id", "lexeme_id", "ord", "definition", "def_lang", "glosses", "register", "labels", "examples", "extra"],
    "concept": ["id", "pos", "lemmas", "gloss", "lexfile"],
    "link": ["src", "dst", "kind", "method", "confidence", "evidence", "sources"],
    "relation": ["src", "dst", "type", "method", "confidence", "sources"],
    "form": ["key", "surface", "lang", "lexeme_id", "kind", "features", "via", "source"],
}
JSON_COLS = {"glosses", "labels", "examples", "extra", "sources", "features", "lemmas", "level"}


class Sink:
    """테이블별 버퍼를 모아 executemany로 넣는다."""

    def __init__(self, path, reopen=False):
        import os
        if os.path.exists(path) and not reopen:
            os.remove(path)
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA journal_mode=OFF")
        self.db.execute("PRAGMA synchronous=OFF")
        if reopen:
            self._indexed = True
        else:
            self.db.executescript(SCHEMA)
        self.buf = {t: [] for t in COLS}
        self.counts = {t: 0 for t in COLS}

    def add(self, table, **row):
        cols = COLS[table]
        vals = []
        for c in cols:
            v = row.get(c)
            if c in JSON_COLS and v is not None and not isinstance(v, str):
                v = dumps(v)
            vals.append(v)
        b = self.buf[table]
        b.append(vals)
        self.counts[table] += 1
        if len(b) >= 20000:
            self.flush(table)

    def flush(self, table=None):
        for t in [table] if table else list(COLS):
            b = self.buf[t]
            if b:
                self.db.executemany(f"INSERT OR REPLACE INTO {t} VALUES ({','.join('?' * len(COLS[t]))})", b)
                self.buf[t] = []
        self.db.commit()

    def make_indexes(self):
        """후처리 연결 단계가 질의할 수 있게 인덱스를 먼저 만든다(한 번만)."""
        self.flush()
        if not getattr(self, "_indexed", False):
            self.db.executescript(INDEXES)
            self._indexed = True
        self.db.commit()

    def finish(self):
        self.make_indexes()
        self.db.close()
