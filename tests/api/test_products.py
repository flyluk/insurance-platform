import pytest
from helpers import login, unique_email

pytestmark = [pytest.mark.api, pytest.mark.story("KAN-5")]


def _auth_headers(api_client, role: str) -> dict[str, str]:
    data = login(api_client, role)
    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest.mark.zephyr("KAN-T28")
def test_agent_lists_published_plans(api_client, agent_headers):
    """Agents can list published plans for quoting."""
    resp = api_client.get(
        "/api/products/plans",
        headers=agent_headers,
        params={"product_code": "AUTO", "status": "PUBLISHED"},
    )
    assert resp.status_code == 200
    plans = resp.json()
    assert plans
    assert plans[0]["status"] == "PUBLISHED"
    assert plans[0]["base_premium"] > 0


@pytest.mark.zephyr("KAN-T29")
def test_agent_forbidden_from_creating_plan(api_client, agent_headers):
    """Agents cannot create product plans."""
    resp = api_client.post(
        "/api/products/plans",
        headers=agent_headers,
        json={
            "product_code": "AUTO",
            "code": f"X-{unique_email('p')[:8]}",
            "name": "Forbidden",
            "base_premium": 10,
        },
    )
    assert resp.status_code == 403


@pytest.mark.zephyr("KAN-T30")
def test_product_role_can_create_and_publish_plan(api_client):
    """Product managers can draft and publish plans."""
    headers = _auth_headers(api_client, "product")
    code = f"T-{unique_email('plan')[:8].upper()}"
    create = api_client.post(
        "/api/products/plans",
        headers=headers,
        json={
            "product_code": "AUTO",
            "code": code,
            "name": "Temp Test Plan",
            "description": "API test",
            "base_premium": 900,
        },
    )
    assert create.status_code == 200
    plan = create.json()
    assert plan["status"] == "DRAFT"

    published = api_client.post(f"/api/products/plans/{plan['id']}/publish", headers=headers)
    assert published.status_code == 200
    assert published.json()["status"] == "PUBLISHED"


@pytest.mark.zephyr("KAN-T31")
def test_quote_with_rider_rates_above_base(api_client, agent_headers):
    """Selecting a rider increases premium vs plan-only quote."""
    plans = api_client.get(
        "/api/products/plans",
        headers=agent_headers,
        params={"product_code": "AUTO", "status": "PUBLISHED"},
    ).json()
    plan = next(p for p in plans if p.get("riders"))
    rider = next(r for r in plan["riders"] if r["status"] == "PUBLISHED")

    party = api_client.post(
        "/api/nb/parties",
        headers=agent_headers,
        json={"full_name": "Rider Party", "email": unique_email("rider")},
    ).json()

    risk = {"vehicle_year": 2022, "drivers": 1, "prior_claims": 0, "driver_age": 34}
    base_quote = api_client.post(
        "/api/nb/quotes",
        headers=agent_headers,
        json={
            "party_id": party["id"],
            "product_code": "AUTO",
            "plan_id": plan["id"],
            "rider_ids": [],
            "risk_attributes": risk,
        },
    ).json()
    rider_quote = api_client.post(
        "/api/nb/quotes",
        headers=agent_headers,
        json={
            "party_id": party["id"],
            "product_code": "AUTO",
            "plan_id": plan["id"],
            "rider_ids": [rider["id"]],
            "risk_attributes": risk,
        },
    ).json()

    base_rated = api_client.post(f"/api/nb/quotes/{base_quote['id']}/rate", headers=agent_headers).json()
    rider_rated = api_client.post(f"/api/nb/quotes/{rider_quote['id']}/rate", headers=agent_headers).json()
    assert rider_rated["annual_premium"] > base_rated["annual_premium"]


@pytest.mark.zephyr("KAN-T32")
def test_published_plans_include_risk_schema(api_client, agent_headers):
    """Published plans expose risk field schema for staff forms."""
    resp = api_client.get(
        "/api/products/plans",
        headers=agent_headers,
        params={"product_code": "AUTO", "status": "PUBLISHED"},
    )
    assert resp.status_code == 200
    plans = resp.json()
    assert plans
    schema = plans[0].get("risk_schema") or []
    assert schema
    keys = {f["key"] for f in schema}
    assert "vehicle_year" in keys
    assert "driver_age" in keys


@pytest.mark.zephyr("KAN-T33")
def test_product_can_update_risk_schema(api_client):
    """Product role can patch plan risk_schema fields."""
    headers = _auth_headers(api_client, "product")
    plans = api_client.get(
        "/api/products/plans",
        headers=headers,
        params={"product_code": "LIFE", "status": "PUBLISHED"},
    ).json()
    plan = plans[0]
    schema = list(plan.get("risk_schema") or [])
    assert schema
    patched = [
        {
            **field,
            "label": field.get("label") or field["key"],
        }
        for field in schema
    ]
    patched.append(
        {
            "key": f"extra_{unique_email('f')[:6]}",
            "label": "Extra test field",
            "type": "text",
            "required": False,
            "default": "",
        }
    )
    resp = api_client.patch(
        f"/api/products/plans/{plan['id']}",
        headers=headers,
        json={"risk_schema": patched},
    )
    assert resp.status_code == 200
    keys = {f["key"] for f in resp.json().get("risk_schema") or []}
    assert patched[-1]["key"] in keys

    # Restore original schema so later runs stay stable
    restore = api_client.patch(
        f"/api/products/plans/{plan['id']}",
        headers=headers,
        json={"risk_schema": schema},
    )
    assert restore.status_code == 200


@pytest.mark.zephyr("KAN-T34")
def test_resolve_quote_returns_effective_rates(api_client, agent_headers):
    """resolve-quote returns plan + rider amounts from rate tables."""
    plans = api_client.get(
        "/api/products/plans",
        headers=agent_headers,
        params={"product_code": "AUTO", "status": "PUBLISHED"},
    ).json()
    plan = next(p for p in plans if p.get("riders"))
    rider = next(r for r in plan["riders"] if r["status"] == "PUBLISHED")

    resp = api_client.post(
        "/api/products/resolve-quote",
        headers=agent_headers,
        json={"plan_id": plan["id"], "rider_ids": [rider["id"]]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan_amount"] > 0
    rider_total = sum(r["amount"] for r in body["riders"])
    assert rider_total > 0
    assert body["total_base"] == pytest.approx(body["plan_amount"] + rider_total)
    assert body.get("plan_rate_version_id")


@pytest.mark.zephyr("KAN-T35")
def test_evaluate_uw_declines_high_claims(api_client, agent_headers):
    """UW thresholds from product-engine decline excessive prior claims."""
    plans = api_client.get(
        "/api/products/plans",
        headers=agent_headers,
        params={"product_code": "AUTO", "status": "PUBLISHED"},
    ).json()
    plan = plans[0]

    resp = api_client.post(
        "/api/products/evaluate-uw",
        headers=agent_headers,
        json={
            "plan_id": plan["id"],
            "product_code": "AUTO",
            "annual_premium": 1000,
            "risk_attributes": {
                "vehicle_year": 2020,
                "drivers": 1,
                "prior_claims": 99,
                "driver_age": 40,
            },
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "DECLINE"


@pytest.mark.zephyr("KAN-T36")
def test_evaluate_uw_accepts_clean_auto(api_client, agent_headers):
    """Clean AUTO risk passes product-engine UW rules."""
    plans = api_client.get(
        "/api/products/plans",
        headers=agent_headers,
        params={"product_code": "AUTO", "status": "PUBLISHED"},
    ).json()
    plan = plans[0]

    resp = api_client.post(
        "/api/products/evaluate-uw",
        headers=agent_headers,
        json={
            "plan_id": plan["id"],
            "product_code": "AUTO",
            "annual_premium": 800,
            "risk_attributes": {
                "vehicle_year": 2022,
                "drivers": 1,
                "prior_claims": 0,
                "driver_age": 40,
            },
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "ACCEPT"


def test_evaluate_uw_respects_empty_plan_rules(api_client):
    """Empty plan uw_rules mean auto-bind; do not fall back to product UW_RULES."""
    headers = _auth_headers(api_client, "product")
    code = f"T-{unique_email('uw')[:8].upper()}"
    create = api_client.post(
        "/api/products/plans",
        headers=headers,
        json={
            "product_code": "AUTO",
            "code": code,
            "name": "Auto-bind Plan",
            "base_premium": 900,
            "uw_rules": {"decline": [], "refer": []},
        },
    )
    assert create.status_code == 200
    plan = create.json()
    assert plan["uw_rules"] == {"decline": [], "refer": []}

    published = api_client.post(f"/api/products/plans/{plan['id']}/publish", headers=headers)
    assert published.status_code == 200

    resp = api_client.post(
        "/api/products/evaluate-uw",
        headers=headers,
        json={
            "plan_id": plan["id"],
            "product_code": "AUTO",
            "annual_premium": 1000,
            "risk_attributes": {
                "vehicle_year": 2020,
                "drivers": 1,
                "prior_claims": 99,
                "driver_age": 40,
            },
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "ACCEPT"
    assert body["plan_id"] == plan["id"]


def test_evaluate_uw_invalid_plan_id_uses_line_defaults_not_another_plan(api_client):
    """Invalid/missing plan_id must not silently substitute another published plan.

    A first-by-sort auto-bind plan would ACCEPT prior_claims=99; product-line
    defaults DECLINE. Response plan_id must stay null when the given id is bad.
    """
    headers = _auth_headers(api_client, "product")
    code = f"T-{unique_email('uwfb')[:8].upper()}"
    create = api_client.post(
        "/api/products/plans",
        headers=headers,
        json={
            "product_code": "AUTO",
            "code": code,
            "name": "Would-be Substituted Auto-bind",
            "base_premium": 900,
            "sort_order": -100,
            "uw_rules": {"decline": [], "refer": []},
        },
    )
    assert create.status_code == 200
    trap_plan = create.json()
    published = api_client.post(f"/api/products/plans/{trap_plan['id']}/publish", headers=headers)
    assert published.status_code == 200

    payload = {
        "product_code": "AUTO",
        "annual_premium": 1000,
        "risk_attributes": {
            "vehicle_year": 2020,
            "drivers": 1,
            "prior_claims": 99,
            "driver_age": 40,
        },
    }
    for plan_id in (None, "00000000-0000-0000-0000-000000000000"):
        body = {**payload}
        if plan_id is not None:
            body["plan_id"] = plan_id
        resp = api_client.post("/api/products/evaluate-uw", headers=headers, json=body)
        assert resp.status_code == 200
        out = resp.json()
        assert out["decision"] == "DECLINE"
        assert out["plan_id"] is None
        assert out["plan_id"] != trap_plan["id"]


def test_evaluate_uw_rejects_mismatched_product_code(api_client):
    """plan_id belonging to another line must not apply that plan's uw_rules."""
    headers = _auth_headers(api_client, "product")
    code = f"T-{unique_email('uwmm')[:8].upper()}"
    create = api_client.post(
        "/api/products/plans",
        headers=headers,
        json={
            "product_code": "AUTO",
            "code": code,
            "name": "Mismatch Auto-bind",
            "base_premium": 900,
            "uw_rules": {"decline": [], "refer": []},
        },
    )
    assert create.status_code == 200
    plan = create.json()
    assert api_client.post(f"/api/products/plans/{plan['id']}/publish", headers=headers).status_code == 200

    # Empty AUTO rules would ACCEPT prior_claims=99; HOME line defaults DECLINE flood+high value.
    # Mismatch must ignore the AUTO plan and use HOME defaults → still DECLINE for flood risk.
    resp = api_client.post(
        "/api/products/evaluate-uw",
        headers=headers,
        json={
            "plan_id": plan["id"],
            "product_code": "HOME",
            "annual_premium": 1000,
            "risk_attributes": {
                "property_value": 600000,
                "flood_zone": True,
                "year_built": 2000,
            },
        },
    )
    assert resp.status_code == 200
    out = resp.json()
    assert out["decision"] == "DECLINE"
    assert out["plan_id"] is None


def test_create_plan_preserves_explicit_empty_risk_schema(api_client):
    """Explicit risk_schema=[] must not be replaced with line RISK_SCHEMAS defaults."""
    headers = _auth_headers(api_client, "product")
    code = f"T-{unique_email('empty')[:8].upper()}"
    create = api_client.post(
        "/api/products/plans",
        headers=headers,
        json={
            "product_code": "AUTO",
            "code": code,
            "name": "No Risk Fields",
            "base_premium": 500,
            "risk_schema": [],
        },
    )
    assert create.status_code == 200
    assert create.json()["risk_schema"] == []


def test_resolve_quote_and_evaluate_uw_require_auth(api_client):
    """Catalog pricing and UW evaluation must not be anonymously callable via gateway."""
    plans = api_client.get("/api/products/plans", params={"product_code": "AUTO", "status": "PUBLISHED"})
    assert plans.status_code == 200
    plan_id = plans.json()[0]["id"]

    resolve = api_client.post("/api/products/resolve-quote", json={"plan_id": plan_id, "rider_ids": []})
    assert resolve.status_code == 401

    evaluate = api_client.post(
        "/api/products/evaluate-uw",
        json={
            "plan_id": plan_id,
            "product_code": "AUTO",
            "annual_premium": 800,
            "risk_attributes": {},
        },
    )
    assert evaluate.status_code == 401


@pytest.mark.zephyr("KAN-T37")
def test_product_can_create_rate_version(api_client):
    """Product role can draft and publish an effective-dated rate version."""
    headers = _auth_headers(api_client, "product")
    plans = api_client.get(
        "/api/products/plans",
        headers=headers,
        params={"product_code": "HOME", "status": "PUBLISHED"},
    ).json()
    plan = plans[0]

    create = api_client.post(
        f"/api/products/plans/{plan['id']}/rates",
        headers=headers,
        json={
            "version_code": f"T-{unique_email('rate')[:8].upper()}",
            "amount": 1300,
            "effective_from": "2030-01-01",
            "effective_to": None,
        },
    )
    assert create.status_code == 200
    rate = create.json()
    assert rate["status"] == "DRAFT"
    assert rate["amount"] == 1300

    published = api_client.post(
        f"/api/products/plans/{plan['id']}/rates/{rate['id']}/publish",
        headers=headers,
    )
    assert published.status_code == 200
    assert published.json()["status"] == "PUBLISHED"


def test_published_catalog_hides_uw_rules_without_auth(api_client, agent_headers):
    """Unauthenticated published plan list must not expose decline/refer thresholds."""
    public = api_client.get(
        "/api/products/plans",
        params={"product_code": "AUTO", "status": "PUBLISHED"},
    )
    assert public.status_code == 200
    assert public.json()
    for plan in public.json():
        assert plan.get("uw_rules") in ({}, None) or plan["uw_rules"] == {}

    authed = api_client.get(
        "/api/products/plans",
        headers=agent_headers,
        params={"product_code": "AUTO", "status": "PUBLISHED"},
    )
    assert authed.status_code == 200
    seeded = next(p for p in authed.json() if p["code"] == "AUTO-BASIC")
    assert seeded["uw_rules"].get("decline") or seeded["uw_rules"].get("refer")


def test_evaluate_uw_uses_unpublished_plan_rules(api_client):
    """In-flight UW must keep plan uw_rules after the plan is unpublished."""
    headers = _auth_headers(api_client, "product")
    code = f"T-{unique_email('uwun')[:8].upper()}"
    create = api_client.post(
        "/api/products/plans",
        headers=headers,
        json={
            "product_code": "AUTO",
            "code": code,
            "name": "Later Unpublished Auto-bind",
            "base_premium": 900,
            "uw_rules": {"decline": [], "refer": []},
        },
    )
    assert create.status_code == 200
    plan = create.json()
    assert api_client.post(f"/api/products/plans/{plan['id']}/publish", headers=headers).status_code == 200
    assert api_client.post(f"/api/products/plans/{plan['id']}/unpublish", headers=headers).status_code == 200

    # Line defaults would DECLINE prior_claims=99; empty plan rules ACCEPT.
    resp = api_client.post(
        "/api/products/evaluate-uw",
        headers=headers,
        json={
            "plan_id": plan["id"],
            "product_code": "AUTO",
            "annual_premium": 1000,
            "risk_attributes": {
                "vehicle_year": 2020,
                "drivers": 1,
                "prior_claims": 99,
                "driver_age": 40,
            },
        },
    )
    assert resp.status_code == 200
    out = resp.json()
    assert out["decision"] == "ACCEPT"
    assert out["plan_id"] == plan["id"]


def test_publishing_rate_end_dates_prior_published_version(api_client):
    """Publishing a new rate must retire overlapping prior published versions."""
    headers = _auth_headers(api_client, "product")
    code = f"T-{unique_email('rate2')[:8].upper()}"
    create = api_client.post(
        "/api/products/plans",
        headers=headers,
        json={
            "product_code": "LIFE",
            "code": code,
            "name": "Rate Overlap Plan",
            "base_premium": 600,
        },
    )
    assert create.status_code == 200
    plan = create.json()
    assert api_client.post(f"/api/products/plans/{plan['id']}/publish", headers=headers).status_code == 200

    rates_before = api_client.get(f"/api/products/plans/{plan['id']}/rates", headers=headers).json()
    prior = next(r for r in rates_before if r["status"] == "PUBLISHED")
    assert prior["effective_to"] is None

    newer = api_client.post(
        f"/api/products/plans/{plan['id']}/rates",
        headers=headers,
        json={
            "version_code": f"T-{unique_email('rv')[:8].upper()}",
            "amount": 777,
            "effective_from": "2026-08-01",
            "effective_to": None,
        },
    )
    assert newer.status_code == 200
    newer_id = newer.json()["id"]
    published = api_client.post(
        f"/api/products/plans/{plan['id']}/rates/{newer_id}/publish",
        headers=headers,
    )
    assert published.status_code == 200

    rates_after = api_client.get(f"/api/products/plans/{plan['id']}/rates", headers=headers).json()
    prior_after = next(r for r in rates_after if r["id"] == prior["id"])
    assert prior_after["status"] == "PUBLISHED"
    assert prior_after["effective_to"] == "2026-07-31"

    resolve = api_client.post(
        "/api/products/resolve-quote",
        headers=headers,
        json={"plan_id": plan["id"], "rider_ids": [], "as_of": "2026-08-15"},
    )
    assert resolve.status_code == 200
    assert resolve.json()["plan_amount"] == 777
