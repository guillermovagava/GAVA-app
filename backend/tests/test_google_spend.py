from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from services import google_usage, google_pricing as gp, google_billing, google_spend
from services.google_places_service import TEXT_SEARCH_SKU
from models import GoogleApiUsage, GoogleSpendDaily


@pytest.fixture()
def client(db, monkeypatch):
    import main
    from routers import scraper

    async def _noop(*a, **k):
        return None
    monkeypatch.setattr(scraper, "_scrape_task", _noop)       # gate tests must not hit Google
    return TestClient(main.app)


def test_lead_photo_is_counted_only_when_google_returns_it(client, db, monkeypatch):
    import httpx
    from models import Lead
    db.add_all([Lead(id=1, business_name="A", photo_ref="places/a/photos/1"),
                Lead(id=2, business_name="B", photo_ref="places/b/photos/1")])
    db.commit()
    real_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(
        lambda req: httpx.Response(200 if "/a/" in req.url.path else 404, content=b"img")), **kw))
    assert client.get("/api/leads/1/photo").status_code == 200
    assert client.get("/api/leads/2/photo").status_code == 404
    assert google_usage.get_month_usage(db=db) == {gp.DETAILS_PHOTOS: 1}
    assert gp.estimate_cost({}, {gp.DETAILS_PHOTOS: 1500})["total_usd"] == pytest.approx(3.5)


# ── persistent counter ───────────────────────────────────────────────────────────────────────────
def test_counter_persists_per_sku_and_month(db):
    google_usage.record_calls(TEXT_SEARCH_SKU, 1)
    google_usage.record_calls(TEXT_SEARCH_SKU, 2)
    google_usage.record_calls(gp.DETAILS_PRO, 1)
    google_usage.record_calls(gp.DETAILS_PRO, 0)               # ignored
    db.add(GoogleApiUsage(month_key="2020-01", sku=TEXT_SEARCH_SKU, calls=99))
    db.commit()
    assert google_usage.get_month_usage(db=db) == {TEXT_SEARCH_SKU: 3, gp.DETAILS_PRO: 1}
    assert google_usage.get_month_usage("2020-01", db=db) == {TEXT_SEARCH_SKU: 99}


def test_legacy_quota_file_is_imported_once(db, tmp_path, monkeypatch):
    import json
    from services import google_quota
    f = tmp_path / "google_quota.json"
    f.write_text(json.dumps({"month": google_usage.month_key(), "used": 42}))
    monkeypatch.setattr(google_quota, "LEGACY_FILE", f)
    assert google_quota.import_legacy_file() == 42
    assert google_usage.get_month_usage(db=db) == {TEXT_SEARCH_SKU: 42}
    assert not f.exists() and (tmp_path / "google_quota.json.migrated").exists()
    assert google_quota.import_legacy_file() == 0
    assert google_quota.get_status()["used"] == 42


# ── estimate endpoint ────────────────────────────────────────────────────────────────────────────
def test_estimate_formula_and_free_tier(client):
    r = client.post("/api/scraper/estimate", json={
        "categories": ["Hotels & Resorts", "Resorts"], "profile_ids": [7],
        "custom_locations": ["Miami Beach, FL", "Aspen, CO"], "max_results_per_city": 40}).json()
    assert r["locations"] == 2 and r["searches"] == 3
    assert r["calls"] == {TEXT_SEARCH_SKU: 2 * 3 * 2}             # locations × searches × ceil(40/20)
    assert r["total_usd"] == 0                                     # inside the 1,000 free calls
    assert r["exceeds_limit"] is False


def test_estimate_accounts_for_the_months_previous_usage(client, db):
    google_usage.record_calls(TEXT_SEARCH_SKU, 1000)               # free cap already used up
    r = client.post("/api/scraper/estimate", json={
        "categories": ["Resorts"], "custom_locations": [f"City {i}, FL" for i in range(10)], "max_results_per_city": 20}).json()
    assert r["calls"][TEXT_SEARCH_SKU] == 10
    assert r["total_usd"] == pytest.approx(10 / 1000 * 35)         # $0.35
    assert r["internal_month_usd"] == 0 and r["projected_month_usd"] == pytest.approx(0.35)


# ── spend limit gate ─────────────────────────────────────────────────────────────────────────────
def test_run_is_blocked_with_409_over_the_limit_and_force_overrides(client, db, monkeypatch):
    monkeypatch.setenv("GOOGLE_SPEND_LIMIT_USD", "0.5")
    google_usage.record_calls(TEXT_SEARCH_SKU, 1000)
    body = {"category_label": "Resorts", "custom_locations": [f"City {i}, FL" for i in range(20)], "max_results_per_city": 20}
    r = client.post("/api/scraper/run", json=body)                 # 20 calls × $0.035 = $0.70 > $0.50
    assert r.status_code == 409
    d = r.json()["detail"]
    assert d["code"] == "spend_limit_exceeded" and d["estimate"]["total_usd"] == pytest.approx(0.7)
    from models import ScrapeJob
    assert db.query(ScrapeJob).count() == 0                        # nothing was created or run
    ok = client.post("/api/scraper/run", json={**body, "force": True})
    assert ok.status_code == 200 and ok.json()["forced"] is True


def test_run_default_limit_is_10_usd_and_inflight_jobs_count(client, db):
    google_usage.record_calls(TEXT_SEARCH_SKU, 1000)
    body = {"category_label": "Resorts", "custom_locations": [f"City {i}, FL" for i in range(150)], "max_results_per_city": 20}
    assert client.post("/api/scraper/run", json=body).status_code == 200       # 150 × .035 = $5.25
    # first job is still in flight (not yet in the counter); the second one sees it and would pass $10
    second = client.post("/api/scraper/run", json={**body, "custom_locations": [f"Town {i}, FL" for i in range(150)]})
    assert second.status_code == 409


def test_real_spend_wins_over_a_lagging_counter(client, db):
    db.add(GoogleSpendDaily(date=datetime.utcnow().date(), sku="x", cost_usd=9.9, credits_usd=0, net_usd=9.9))
    db.add(google_billing.GoogleBillingSync(status="ok", message="", rows=1))
    db.commit()
    import os
    os.environ["GOOGLE_BILLING_BQ_TABLE"] = "p.d.gcp_billing_export_v1_X"; os.environ["GOOGLE_BILLING_SA_JSON"] = "{}"
    try:
        google_usage.record_calls(TEXT_SEARCH_SKU, 1000)
        r = client.post("/api/scraper/run", json={"category_label": "Resorts", "custom_locations": [f"C{i}, FL" for i in range(10)],
                                                  "max_results_per_city": 20})
        assert r.status_code == 409          # 9.90 real + 0.35 estimate > 10
    finally:
        os.environ.pop("GOOGLE_BILLING_BQ_TABLE"); os.environ.pop("GOOGLE_BILLING_SA_JSON")


# ── billing sync + summary ───────────────────────────────────────────────────────────────────────
def test_summary_without_billing_config_says_not_configured_not_zero(client, db):
    google_usage.record_calls(TEXT_SEARCH_SKU, 1500)
    s = client.get("/api/google-spend/summary").json()
    assert s["real"]["status"] == "not_configured" and s["real"]["net_usd"] is None
    assert s["internal"]["estimated_usd"] == pytest.approx(500 / 1000 * 35)   # 1,500 calls − 1,000 free = 500 × $35/1000
    assert s["free_remaining"][TEXT_SEARCH_SKU]["free_remaining"] == 0 and s["scraper_sku"] == TEXT_SEARCH_SKU


@pytest.fixture()
def billing_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_BILLING_BQ_TABLE", "proj.ds.gcp_billing_export_v1_ABC")
    monkeypatch.setenv("GOOGLE_BILLING_SA_JSON", '{"type": "service_account"}')


def _rows(day):
    return [{"day": day, "sku": "Places API Text Search Enterprise", "currency": "USD", "cost": 3.5, "credits": -1.0},
            {"day": day, "sku": "Places API Place Details Pro", "currency": "USD", "cost": 1.0, "credits": 0.0},
            {"day": day, "sku": "Other", "currency": "MXN", "cost": 99.0, "credits": 0.0}]


def test_sync_upserts_per_day_and_sku_and_reports_net(client, db, billing_env, monkeypatch):
    today = datetime.utcnow().date()
    monkeypatch.setattr(google_billing, "_query_rows", lambda start, end: _rows(today))
    res = client.post("/api/google-spend/sync").json()
    assert res["status"] == "ok" and res["rows"] == 2                      # MXN row ignored
    client.post("/api/google-spend/sync")                                  # second sync must update, not duplicate
    assert db.query(GoogleSpendDaily).count() == 2
    real = res["summary"]["real"]
    assert real["status"] == "ok" and real["cost_usd"] == pytest.approx(4.5)
    assert real["credits_usd"] == pytest.approx(-1.0) and real["net_usd"] == pytest.approx(3.5)
    assert res["summary"]["last_sync_at"]
    assert res["summary"]["projection"]["basis"] == "real"


def test_sync_with_no_data_or_missing_table_is_a_clear_state_not_zero(client, db, billing_env, monkeypatch):
    monkeypatch.setattr(google_billing, "_query_rows", lambda s, e: [])
    r = client.post("/api/google-spend/sync").json()
    assert r["status"] == "no_data" and r["summary"]["real"]["net_usd"] is None
    assert "sin datos de facturación" in r["summary"]["real"]["message"].lower()

    class NotFound(Exception):
        pass

    def boom(s, e):
        raise NotFound("404 Not found: Table")
    monkeypatch.setattr(google_billing, "_query_rows", boom)
    r = client.post("/api/google-spend/sync").json()
    assert r["status"] == "no_data" and r["summary"]["real"]["net_usd"] is None


def test_sync_errors_are_reported_without_leaking_credentials(client, db, billing_env, monkeypatch):
    def boom(s, e):
        raise PermissionError("Access Denied: BigQuery BigQuery: Permission bigquery.jobs.create denied")
    monkeypatch.setattr(google_billing, "_query_rows", boom)
    r = client.post("/api/google-spend/sync").json()
    assert r["status"] == "error" and "service_account" not in str(r)


def test_sync_without_config_is_not_configured(client, db):
    r = client.post("/api/google-spend/sync").json()
    assert r["status"] == "not_configured"


def test_bad_table_name_is_rejected_before_it_reaches_sql(monkeypatch):
    monkeypatch.setenv("GOOGLE_BILLING_BQ_TABLE", "x`; DROP TABLE y; --")
    monkeypatch.setenv("GOOGLE_BILLING_SA_JSON", "{}")
    with pytest.raises(ValueError):
        google_billing._query_rows(datetime(2026, 10, 1), datetime(2026, 10, 2))


def test_projection_uses_daily_average(client, db, monkeypatch):
    import calendar
    google_usage.record_calls(TEXT_SEARCH_SKU, 2000)                      # internal: 1000 billable → $35
    p = client.get("/api/google-spend/summary").json()["projection"]
    assert p["basis"] == "internal"
    assert p["projected_usd"] == pytest.approx(35 / p["days_elapsed"] * p["days_in_month"], abs=0.01)
