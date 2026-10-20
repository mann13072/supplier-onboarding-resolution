"""Adapt the existing store to Cloudflare's synchronous SQLite storage API."""
from contextlib import contextmanager

from .store import Store


class Row(dict):
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


class Cursor:
    def __init__(self, rows):
        self.rows = iter(rows)

    def __iter__(self):
        return self.rows

    def fetchone(self):
        return next(self.rows, None)


class Connection:
    def __init__(self, sql):
        self.sql = sql

    def execute(self, query, params=()):
        # transactionSync wraps the entire Store operation on Workers.
        if query == "BEGIN IMMEDIATE":
            return Cursor([])
        cursor = self.sql.exec(query, *params)
        columns = list(cursor.columnNames)
        rows = [Row(zip(columns, list(row))) for row in cursor.raw().toArray()]
        return Cursor(rows)

    def executescript(self, query):
        self.sql.exec(query)


class CloudflareStore(Store):
    def __init__(self, storage):
        self.storage = storage
        self.db = Connection(storage.sql)
        self._transaction(self._initialize)

    def _initialize(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS contacts (scope TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS audit (
                seq INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL,
                actor TEXT NOT NULL, action TEXT NOT NULL, details TEXT NOT NULL, recorded_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)
        if not self.db.execute("SELECT 1 FROM cases LIMIT 1").fetchone():
            self._seed(self.db, "accepted")

    @contextmanager
    def connection(self):
        yield self.db

    def _transaction(self, fn):
        # Keep Python results/exceptions on this side of the JS callback boundary.
        result, error = [], []

        def run():
            try:
                result.append(fn())
            except Exception as exc:
                error.append(exc)
                raise

        try:
            self.storage.transactionSync(run)
        except Exception:
            if error:
                raise error[0]
            raise
        return result[0]

    def reset(self, variant):
        return self._transaction(lambda: super(CloudflareStore, self).reset(variant))

    def mutate(self, *args, **kwargs):
        return self._transaction(lambda: super(CloudflareStore, self).mutate(*args, **kwargs))
