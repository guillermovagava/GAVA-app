import os
import sys
import tempfile
from pathlib import Path

# Isolated DB for the whole test run — must be set BEFORE importing the app (database.py reads it at import).
_tmp = tempfile.mkdtemp(prefix="gava-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
for var in ("GOOGLE_BILLING_BQ_TABLE", "GOOGLE_BILLING_SA_JSON", "GOOGLE_SPEND_LIMIT_USD", "GOOGLE_SPEND_WARN_USD"):
    os.environ.pop(var, None)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402


@pytest.fixture()
def db():
    from database import SessionLocal, Base, engine
    import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    s = SessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        s.execute(table.delete())
    s.commit()
    from services import google_spend
    google_spend._inflight.clear()
    yield s
    s.close()
