import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://mycompassion.localhost:8069"
LOGIN = "admin"
PASSWORD = "admin"


def test_donation_cycle_e2e(page: Page):
    page.set_viewport_size({"width": 1920, "height": 1080})

    # -----------------------------------------------------------------------
    # LOGIN
    # -----------------------------------------------------------------------
    print(f"Logge ein als {LOGIN}...")
    page.goto(f"{BASE_URL}/web/login")
    page.fill("input[name='login']", LOGIN)
    page.fill("input[name='password']", PASSWORD)
    page.click("button[type='submit']")

    page.wait_for_url("**/web**", timeout=15000)
    print("Login erfolgreich.")

    # -----------------------------------------------------------------------
    # DASHBOARD & NAVIGATION
    # -----------------------------------------------------------------------
    print("Gehe zum Dashboard...")
    page.goto(f"{BASE_URL}/my2/dashboard")

    try:
        error_modal = page.locator(".o_error_detail_modal")
        if error_modal.is_visible(timeout=3000):
            print("Style Error gefunden -> Schließe Modal.")
            page.locator(".modal-header button.close").click()
    except:
        pass

    page.locator("a[href*='/my2/gifts']").first.click()
    expect(page).to_have_url(f"{BASE_URL}/my2/gifts")

    # -----------------------------------------------------------------------
    # PRODUKT WÄHLEN
    # -----------------------------------------------------------------------
    page.locator(".card.vignette", has_text="Goat Donation Fund").click()
    expect(page.locator(".donation-details-header h2")).to_contain_text("Goat Donation Fund")

    # -----------------------------------------------------------------------
    # KONFIGURIEREN & ADD TO CART
    # -----------------------------------------------------------------------
    print("Konfiguriere Spende...")
    page.locator(".my2_donation_form .donation-frequency label", has_text="Monthly").click()
    page.locator(".my2_donation_form label[for='donation-suggested-medium']").click()

    print("In den Warenkorb...")
    page.locator("button", has_text="Add & check out").click()

    # -----------------------------------------------------------------------
    # WARENKORB PRÜFEN & LÖSCHEN
    # -----------------------------------------------------------------------
    expect(page.locator("h1")).to_contain_text("Gift Package")
    expect(page.locator("body")).to_contain_text("Goat Donation Fund")

    expect(page.locator(".bg-light-green", has_text="Total amount")).to_contain_text("100")

    page.locator("i.icon-trash01").first.click()

    expect(page.locator("body")).not_to_contain_text("Goat Donation Fund")
    expect(page.locator("body")).to_contain_text("Your Gift Package is empty")

