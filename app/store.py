from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

from .domain import RuleError, RuleBasedSummary, milestone
from .fixtures import ROLLOUT_ID, DEMO_TIME, scope, seed_cases


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS contacts (scope TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS audit (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL,
                    actor TEXT NOT NULL, action TEXT NOT NULL, details TEXT NOT NULL, recorded_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            ''')
            if not db.execute("SELECT 1 FROM cases LIMIT 1").fetchone():
                self._seed(db, "accepted")

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _seed(self, db, variant):
        db.execute("DELETE FROM audit")
        db.execute("DELETE FROM contacts")
        db.execute("DELETE FROM cases")
        for c in seed_cases():
            db.execute("INSERT INTO cases VALUES (?,?)", (c["id"], json.dumps(c)))
            db.execute("INSERT INTO contacts VALUES (?,?)", (scope(c), json.dumps(c["initialContact"])))
            self.audit(db, c["id"], "Fixture loader", "Case loaded", "Synthetic source snapshot and events loaded.")
        db.execute("INSERT OR REPLACE INTO settings VALUES ('variant',?)", (variant,))

    def reset(self, variant):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self._seed(db, variant)

    @staticmethod
    def load(db, cid):
        row = db.execute("SELECT payload FROM cases WHERE id=?", (cid,)).fetchone()
        if not row:
            raise RuleError("Supplier case not found.", 404)
        return json.loads(row[0])

    @staticmethod
    def audit(db, cid, actor, action, details):
        db.execute("INSERT INTO audit(case_id,actor,action,details,recorded_at) VALUES (?,?,?,?,?)",
                   (cid, actor, action, details, datetime.now(timezone.utc).isoformat()))

    def view(self, db, c):
        result = deepcopy(c)
        result["currentContact"] = json.loads(db.execute("SELECT payload FROM contacts WHERE scope=?", (scope(c),)).fetchone()[0])
        result["scopeKey"] = scope(c)
        result["assessment"] = RuleBasedSummary().summarize(c)
        result["milestone"] = milestone(c)
        result["audit"] = [dict(row) for row in db.execute("SELECT * FROM audit WHERE case_id=? ORDER BY seq", (c["id"],))]
        result["variant"] = db.execute("SELECT value FROM settings WHERE key='variant'").fetchone()[0]
        result["demoTime"] = DEMO_TIME
        return result

    def get(self, cid):
        with self.connection() as db:
            return self.view(db, self.load(db, cid))

    def rollout(self):
        with self.connection() as db:
            cases = [self.view(db, json.loads(r[0])) for r in db.execute("SELECT payload FROM cases ORDER BY rowid")]
            return dict(id=ROLLOUT_ID, name="November supplier rollout", buyer="Nordtal Motion GmbH",
                        plant="Leipzig · LEI-01", target="2026-11-16", demoTime=DEMO_TIME,
                        variant=cases[0]["variant"], cases=cases)

    def mutate(self, cid, version, actor, action, fn, idempotent=None):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            c = self.load(db, cid)
            if idempotent and idempotent(c):
                return self.view(db, c)
            if c["version"] != version:
                raise RuleError("This case changed. Refresh it and review the latest evidence before continuing.")
            immutable = deepcopy(c["sourceSnapshot"])
            details = fn(c, db)
            assert c["sourceSnapshot"] == immutable, "ERP source snapshot must remain immutable"
            c["version"] += 1
            db.execute("UPDATE cases SET payload=? WHERE id=?", (json.dumps(c), cid))
            self.audit(db, cid, actor, action, details)
            return self.view(db, c)
