import re

import pytest
from helpers import create_auto_quote, wait_until
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.ui


def create_submitted_auto_application(api_client, agent_headers):
    _, quote = create_auto_quote(api_client, agent_headers)
    rated = api_client.post(f"/api/nb/quotes/{quote['id']}/rate", headers=agent_headers)
    rated.raise_for_status()
    submitted = api_client.post(f"/api/nb/quotes/{quote['id']}/submit", headers=agent_headers)
    submitted.raise_for_status()
    return submitted.json()


def login_as(page: Page, ui_base: str, email: str, password: str) -> None:
    page.goto(f"{ui_base}/login")
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Sign in").click()
    expect(page.get_by_role("link", name="Meridian")).to_be_visible(timeout=15000)
    expect(page.get_by_text(re.compile(r"^Welcome,"))).to_be_visible()


def nav(page: Page):
    return page.get_by_role("navigation")


@pytest.mark.story("KAN-1")
def test_login_agent(page: Page, ui_base: str):
    """Staff UI login succeeds for the demo agent."""
    login_as(page, ui_base, "agent@insurance.local", "agent123")
    expect(nav(page).get_by_role("link", name="New Business")).to_be_visible()


@pytest.mark.story("KAN-1")
def test_login_failure(page: Page, ui_base: str):
    """Staff UI login shows an error for bad credentials."""
    page.goto(f"{ui_base}/login")
    page.get_by_label("Email").fill("agent@insurance.local")
    page.get_by_label("Password").fill("wrong-password")
    page.get_by_role("button", name="Sign in").click()
    expect(page.get_by_text("Login failed")).to_be_visible(timeout=10000)


@pytest.mark.story("KAN-2")
def test_create_quote_with_form_fields(page: Page, ui_base: str):
    """Create, rate, and submit a quote from the New Business UI."""
    login_as(page, ui_base, "agent@insurance.local", "agent123")
    nav(page).get_by_role("link", name="New Business").click()
    expect(page.get_by_role("heading", name="New Business")).to_be_visible()

    suffix = page.evaluate("() => Date.now()")
    party_form = page.locator("form.panel.stack").filter(has_text="New party")
    party_form.get_by_label("Full name").fill(f"UI Party {suffix}")
    party_form.get_by_label("Email").fill(f"ui-party-{suffix}@example.com")
    party_form.get_by_role("button", name="Save party").click()

    quote_form = page.locator("form.panel.stack").filter(has_text="New quote")
    expect(quote_form.get_by_label("Party")).to_contain_text(f"UI Party {suffix}", timeout=10000)

    quote_form.get_by_label("Product").select_option("AUTO")
    expect(quote_form.get_by_label("Basic plan")).not_to_have_value("", timeout=10000)
    quote_form.get_by_label("Vehicle year").fill("2022")
    quote_form.get_by_label("Drivers").fill("1")
    quote_form.get_by_label("Prior claims").fill("0")
    quote_form.get_by_label("Driver age").fill("34")
    quote_form.get_by_role("button", name="Create quote").click()
    expect(page.get_by_text("Quote created")).to_be_visible(timeout=10000)

    quotes_panel = page.locator("div.panel").filter(has_text="Quotes")
    quotes_panel.get_by_role("button", name="Rate").first.click()
    expect(quotes_panel.get_by_text("RATED").first).to_be_visible(timeout=10000)

    quotes_panel.get_by_role("button", name="Submit").first.click()
    expect(page.get_by_text("Submitted to underwriting")).to_be_visible(timeout=10000)


@pytest.mark.story("KAN-3")
def test_underwriting_case_details(page: Page, ui_base: str, api_client, agent_headers):
    """Underwriting UI shows case details for a submitted application."""
    application = create_submitted_auto_application(api_client, agent_headers)

    def underwriting_case():
        cases = api_client.get("/api/uw/cases", headers=agent_headers)
        cases.raise_for_status()
        return next((case for case in cases.json() if case["application_id"] == application["id"]), None)

    wait_until(underwriting_case, timeout=45, desc=f"underwriting case for application {application['id']}")

    login_as(page, ui_base, "uw@insurance.local", "uw123456")
    nav(page).get_by_role("link", name="Underwriting").click()
    expect(page.get_by_role("heading", name="Underwriting")).to_be_visible()

    details_btn = page.get_by_role("button", name="Details").first
    expect(details_btn).to_be_visible(timeout=15000)
    details_btn.click()
    expect(page.get_by_role("heading", name="Case details")).to_be_visible()
    expect(page.get_by_text("Risk attributes")).to_be_visible()


@pytest.mark.story("KAN-3")
def test_policy_list_and_detail(page: Page, ui_base: str, api_client, agent_headers):
    """Policy Admin UI lists policies and opens a detail page."""
    application = create_submitted_auto_application(api_client, agent_headers)

    def bound_application():
        applications = api_client.get("/api/nb/applications", headers=agent_headers)
        applications.raise_for_status()
        match = next((app for app in applications.json() if app["id"] == application["id"]), None)
        if match and match.get("status") == "BOUND" and match.get("policy_id"):
            return match
        return None

    wait_until(bound_application, timeout=45, desc=f"application {application['id']} BOUND")

    login_as(page, ui_base, "agent@insurance.local", "agent123")
    nav(page).get_by_role("link", name="Policies").click()
    expect(page.get_by_role("heading", name="Policy Admin")).to_be_visible()

    view = page.get_by_role("link", name="View").first
    expect(view).to_be_visible(timeout=15000)
    view.click()
    expect(page).to_have_url(re.compile(r".*/policies/.+"))
    expect(page.get_by_text("Policy details")).to_be_visible()
    expect(page.get_by_role("heading", name="Risk attributes")).to_be_visible()
    expect(page.get_by_role("heading", name="Endorsements")).to_be_visible()
