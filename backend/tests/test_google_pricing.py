import pytest
from services import google_pricing as gp
from services.google_places_service import TEXT_SEARCH_FIELD_MASK, TEXT_SEARCH_SKU


def test_zero_calls_cost_nothing():
    assert gp.estimate_cost({}, {})["total_usd"] == 0
    assert gp.estimate_cost({}, {gp.DETAILS_PRO: 0})["total_usd"] == 0


def test_place_details_pro_5988_calls_in_a_fresh_month():
    # (5988 − 5000 free) / 1000 × $17 = $16.796
    r = gp.estimate_cost({}, {gp.DETAILS_PRO: 5988})
    assert r["total_usd"] == pytest.approx(16.79, abs=0.01)
    b = r["breakdown"][gp.DETAILS_PRO]
    assert (b["free_calls"], b["billable_calls"]) == (5000, 988)


def test_24_text_search_pro_calls_stay_inside_the_free_cap():
    r = gp.estimate_cost({}, {gp.TEXT_SEARCH_PRO: 24})
    assert r["total_usd"] == 0
    assert r["breakdown"][gp.TEXT_SEARCH_PRO]["free_remaining_before"] == 5000


def test_free_cap_is_consumed_once_per_month_not_per_run():
    one_go = gp.estimate_cost({}, {gp.DETAILS_PRO: 6000})["total_usd"]
    first = gp.estimate_cost({}, {gp.DETAILS_PRO: 3000})["total_usd"]
    second = gp.estimate_cost({gp.DETAILS_PRO: 3000}, {gp.DETAILS_PRO: 3000})["total_usd"]
    assert first == 0 and second == pytest.approx(one_go) == pytest.approx(17.0)
    # once the cap is gone, every extra call is billable from the first one
    assert gp.estimate_cost({gp.DETAILS_PRO: 5000}, {gp.DETAILS_PRO: 1000})["total_usd"] == pytest.approx(17.0)


def test_tier_price_depends_on_the_months_total_not_the_run():
    # 99,000 billable already; 2,000 more cross the 100k boundary: 1,000 × $17 + 1,000 × $13.60 per 1000
    before = {gp.DETAILS_PRO: 5000 + 99_000}
    assert gp.estimate_cost(before, {gp.DETAILS_PRO: 2000})["total_usd"] == pytest.approx(17.0 + 13.6)
    # same run later in the month (already past the boundary) is cheaper
    assert gp.estimate_cost({gp.DETAILS_PRO: 5000 + 150_000}, {gp.DETAILS_PRO: 2000})["total_usd"] == pytest.approx(27.2)


def test_text_search_enterprise_current_scraper_sku():
    assert gp.estimate_cost({}, {gp.TEXT_SEARCH_ENTERPRISE: 1000})["total_usd"] == 0       # free cap 1,000
    assert gp.estimate_cost({}, {gp.TEXT_SEARCH_ENTERPRISE: 2000})["total_usd"] == pytest.approx(35.0)


def test_ids_only_is_unlimited_and_unknown_skus_are_flagged_not_priced():
    assert gp.estimate_cost({}, {gp.TEXT_SEARCH_IDS_ONLY: 10_000_000})["total_usd"] == 0
    r = gp.estimate_cost({}, {"Some New SKU": 10})
    assert r["total_usd"] == 0 and r["breakdown"]["Some New SKU"]["priced"] is False


def test_every_required_sku_is_configured():
    for sku in (gp.TEXT_SEARCH_PRO, gp.TEXT_SEARCH_ENTERPRISE, gp.DETAILS_PRO, gp.DETAILS_ENTERPRISE,
                gp.DETAILS_ENTERPRISE_ATMOSPHERE, gp.NEARBY_SEARCH_PRO, gp.DETAILS_ESSENTIALS, gp.TEXT_SEARCH_IDS_ONLY):
        assert sku in gp.SKUS
    assert gp.SKUS[gp.DETAILS_ESSENTIALS]["free_cap"] == 10_000


def test_scrapers_field_mask_maps_to_text_search_enterprise():
    # phone + website are Enterprise fields
    assert gp.classify_field_mask(TEXT_SEARCH_FIELD_MASK) == "enterprise"
    assert TEXT_SEARCH_SKU == gp.TEXT_SEARCH_ENTERPRISE


def test_field_mask_tiers_go_up_with_the_fields_requested():
    pro = "places.id,places.displayName,places.formattedAddress,places.location,places.photos,nextPageToken"
    assert gp.text_search_sku(pro) == gp.TEXT_SEARCH_PRO
    assert gp.text_search_sku("places.id,nextPageToken") == gp.TEXT_SEARCH_IDS_ONLY
    assert gp.text_search_sku(pro + ",places.regularOpeningHours") == gp.TEXT_SEARCH_ENTERPRISE
    assert gp.text_search_sku(pro + ",places.reviews") == gp.TEXT_SEARCH_ENTERPRISE_ATMOSPHERE
    assert gp.place_details_sku(pro + ",places.websiteUri") == gp.DETAILS_ENTERPRISE


def test_normalize_sku_strips_region_suffixes_longest_match_first():
    assert gp.normalize_sku("Places API Text Search Enterprise + Atmosphere - Americas") == gp.TEXT_SEARCH_ENTERPRISE_ATMOSPHERE
    assert gp.normalize_sku("Places API Text Search Enterprise") == gp.TEXT_SEARCH_ENTERPRISE
