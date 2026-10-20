"""
One-time copy of the local SQLite database into the Railway PostgreSQL database.

Usage (from the backend/ folder):
    set DATABASE_URL=<Railway DATABASE_PUBLIC_URL>
    python migrate_to_postgres.py [path\\to\\gava_leads.db]
"""
import os
import sqlite3
import sys

from sqlalchemy import Boolean, text

if not os.getenv("DATABASE_URL"):
    sys.exit("Set DATABASE_URL to the Railway DATABASE_PUBLIC_URL first.")

from database import Base, engine
import models  # noqa: F401

SQLITE_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "gava_leads.db")
TABLES = ["leads", "email_logs", "scrape_jobs", "search_profiles"]

src = sqlite3.connect(SQLITE_PATH)
src.row_factory = sqlite3.Row
Base.metadata.create_all(bind=engine)

with engine.begin() as dst:
    for name in TABLES:
        table = Base.metadata.tables[name]
        if not src.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone():
            print(f"{name}: not in SQLite, skipped")
            continue
        if dst.execute(text(f"SELECT COUNT(*) FROM {name}")).scalar():
            print(f"{name}: already has rows in PostgreSQL, skipped")
            continue

        src_cols = {r[1] for r in src.execute(f"PRAGMA table_info({name})")}
        cols = [c for c in table.columns if c.name in src_cols]
        rows = []
        for r in src.execute(f"SELECT {', '.join(c.name for c in cols)} FROM {name}"):
            row = {}
            for c in cols:
                v = r[c.name]
                if isinstance(c.type, Boolean) and v is not None:
                    v = bool(v)
                row[c.name] = v
            rows.append(row)

        if rows:
            dst.execute(table.insert(), rows)
            dst.execute(text(f"SELECT setval(pg_get_serial_sequence('{name}', 'id'), (SELECT MAX(id) FROM {name}))"))
        print(f"{name}: copied {len(rows)} rows")

print("Done.")
