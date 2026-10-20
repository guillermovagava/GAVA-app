"""
Real Google Maps Platform spend, read from the Cloud Billing export in BigQuery.

Config (env vars only — never in code or logs):
  GOOGLE_BILLING_BQ_TABLE  project.dataset.gcp_billing_export_v1_XXXXXX
  GOOGLE_BILLING_SA_JSON   service-account key (JSON) with BigQuery Data Viewer + BigQuery Job User

The export only contains data from the day it was enabled, and rows arrive with a delay of hours.
"""
from __future__ import annotations
import json
import os
import re
from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import GoogleSpendDaily, GoogleBillingSync

_TABLE_RE = re.compile(r"^[A-Za-z0-9_.\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+$")


def is_configured() -> bool:
    return bool(os.getenv("GOOGLE_BILLING_BQ_TABLE") and os.getenv("GOOGLE_BILLING_SA_JSON"))


def _client():
    """BigQuery client from the service-account JSON in the environment (imported lazily)."""
    from google.cloud import bigquery
    from google.oauth2 import service_account
    info = json.loads(os.environ["GOOGLE_BILLING_SA_JSON"])
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/bigquery"])
    return bigquery.Client(credentials=creds, project=info.get("project_id"))


def _query_rows(start: datetime, end: datetime) -> list[dict]:
    from google.cloud import bigquery
    table = os.environ["GOOGLE_BILLING_BQ_TABLE"].strip()
    if not _TABLE_RE.match(table):            # it is interpolated into SQL: accept only a plain table id
        raise ValueError("GOOGLE_BILLING_BQ_TABLE no tiene el formato proyecto.dataset.tabla")
    sql = f"""
        SELECT DATE(usage_start_time) AS day,
               sku.description AS sku,
               currency,
               SUM(cost) AS cost,
               SUM(IFNULL((SELECT SUM(c.amount) FROM UNNEST(credits) AS c), 0)) AS credits
        FROM `{table}`
        WHERE usage_start_time >= @start AND usage_start_time < @end
          AND REGEXP_CONTAINS(service.description, r'(?i)maps|places')
        GROUP BY day, sku, currency
    """
    job = _client().query(sql, job_config=bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("start", "TIMESTAMP", start),
        bigquery.ScalarQueryParameter("end", "TIMESTAMP", end),
    ]))
    return [dict(r) for r in job.result()]


def _log(db: Session, status: str, message: str, rows: int = 0) -> dict:
    db.add(GoogleBillingSync(status=status, message=message, rows=rows))
    db.commit()
    old = db.query(GoogleBillingSync.id).order_by(GoogleBillingSync.id.desc()).offset(50).all()
    if old:
        db.query(GoogleBillingSync).filter(GoogleBillingSync.id.in_([i for (i,) in old])).delete(synchronize_session=False)
        db.commit()
    return {"status": status, "message": message, "rows": rows}


def sync(db: Session) -> dict:
    """
    Pull this month's (plus the last 3 days of the previous month, for late-arriving rows) Maps/Places
    cost and credits from BigQuery and upsert them per (date, sku) into google_spend_daily.
    """
    if not is_configured():
        return _log(db, "not_configured", "Faltan GOOGLE_BILLING_BQ_TABLE y/o GOOGLE_BILLING_SA_JSON.")
    today = datetime.utcnow().date()
    start_day = min(today.replace(day=1), today - timedelta(days=3))
    start = datetime(start_day.year, start_day.month, start_day.day)
    end = datetime(today.year, today.month, today.day) + timedelta(days=1)
    try:
        rows = _query_rows(start, end)
    except Exception as e:
        name = type(e).__name__
        if name in ("NotFound",):
            return _log(db, "no_data", "La tabla de exportación aún no existe o no tiene datos (la exportación solo guarda datos desde el día en que se activó).")
        # Only the exception class + Google's message; never the credentials.
        return _log(db, "error", f"{name}: {str(e)[:300]}")

    usd = [r for r in rows if (r.get("currency") or "USD") == "USD"]
    skipped = len(rows) - len(usd)
    if not usd:
        msg = "Sin datos de facturación todavía para Maps/Places."
        if skipped:
            msg += f" ({skipped} filas en otra moneda ignoradas: la cuenta de facturación debe estar en USD.)"
        return _log(db, "no_data", msg)

    now = datetime.utcnow()
    for r in usd:
        cost, credits = float(r["cost"] or 0), float(r["credits"] or 0)
        day = r["day"] if isinstance(r["day"], date) else date.fromisoformat(str(r["day"]))
        row = db.query(GoogleSpendDaily).filter(GoogleSpendDaily.date == day, GoogleSpendDaily.sku == r["sku"]).first()
        if row is None:
            row = GoogleSpendDaily(date=day, sku=r["sku"])
            db.add(row)
        row.cost_usd, row.credits_usd, row.net_usd, row.synced_at = cost, credits, cost + credits, now
    db.commit()
    msg = f"{len(usd)} filas sincronizadas." + (f" {skipped} en otra moneda ignoradas." if skipped else "")
    return _log(db, "ok", msg, len(usd))


def last_sync(db: Session) -> GoogleBillingSync | None:
    return db.query(GoogleBillingSync).order_by(GoogleBillingSync.id.desc()).first()


def real_spend(db: Session, month: str) -> dict:
    """
    Real net spend for 'YYYY-MM'. net_usd is None (never 0) unless there is actual billing data, and
    `status` says why: not_configured | pending | no_data | error | ok.
    """
    ls = last_sync(db)
    out = {"status": "not_configured", "message": "Facturación no configurada.", "net_usd": None, "cost_usd": None,
           "credits_usd": None, "by_sku": [], "last_sync_at": ls.synced_at.isoformat() + "Z" if ls else None}
    if not is_configured():
        return out
    if ls is None:
        return {**out, "status": "pending", "message": "Aún no se ha sincronizado la facturación."}
    y, m = int(month[:4]), int(month[5:7])
    first, nxt = date(y, m, 1), date(y + (m == 12), (m % 12) + 1, 1)
    q = db.query(GoogleSpendDaily).filter(GoogleSpendDaily.date >= first, GoogleSpendDaily.date < nxt)
    rows = q.all()
    if rows:
        by_sku: dict[str, dict] = {}
        for r in rows:
            d = by_sku.setdefault(r.sku, {"sku": r.sku, "cost_usd": 0.0, "credits_usd": 0.0, "net_usd": 0.0})
            d["cost_usd"] += r.cost_usd; d["credits_usd"] += r.credits_usd; d["net_usd"] += r.net_usd
        tot_cost, tot_cred = sum(r.cost_usd for r in rows), sum(r.credits_usd for r in rows)
        return {**out, "status": "ok" if ls.status == "ok" else ls.status,
                "message": ls.message if ls.status != "ok" else "", "net_usd": round(tot_cost + tot_cred, 4),
                "cost_usd": round(tot_cost, 4), "credits_usd": round(tot_cred, 4),
                "by_sku": [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()} for d in by_sku.values()]}
    if ls.status == "ok":      # synced fine, but this month has no rows yet
        return {**out, "status": "no_data", "message": "Sin datos de facturación todavía para este mes."}
    return {**out, "status": ls.status, "message": ls.message}
