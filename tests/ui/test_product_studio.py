import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.ui, pytest.mark.story("KAN-5")]


@pytest.mark.zephyr("KAN-T38")
def test_product_studio_login(page: Page, product_ui_base: str):
    """Product Studio login succeeds for the product role."""
    page.goto(f"{product_ui_base}/login")
    page.get_by_label("Email").fill("product@insurance.local")
    page.get_by_label("Password").fill("product123")
    page.get_by_role("button", name="Sign in").click()
    expect(page.locator(".brand")).to_have_text("Product Studio", timeout=15000)
    expect(page.get_by_role("heading", name="Product lines")).to_be_visible()
    expect(page.get_by_text("Product Manager · product")).to_be_visible()
    expect(page.get_by_role("navigation").get_by_role("link", name="Plans")).to_be_visible()
