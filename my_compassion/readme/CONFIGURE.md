This module is country-agnostic and multi-company aware: a multi-company
instance runs one MyCompassion website per country, each flagged with the
`is_my_compassion` field. Each national office configures its website:

- **Website record**: `my_compassion.my2_website` ships flagged, with a
  placeholder domain; set the real domain and languages after install.
  Additional country websites are created normally, flagged, and get the
  theme applied by the module hook on the next upgrade.
- **Company data**: the portal renders the website company's phone and email
  (donation help blocks, account-deletion help). Set them on each company.
- **Sponsorship products**: the wizard copy renders the monthly amounts of the
  products with `default_code` `sponsorship` and `fund_gen` (the same products
  the contract lines use); a company-specific product wins over a shared one.
- **Website fields** (optional, per website):
  - `data_change_notification_email`: recipient of the partner data-change
    notifications (defaults to the website company's email).
  - `sponsor_child_url`: target of the "start a sponsorship" link shown to
    users without sponsorships (defaults to `/my2/children`).
  - `my2_duplicate_review_user_id` (MyCompassion tab): who gets a to-do when
    a visitor who sponsored without logging in used the email of a known
    donor. The visitor always gets a new contact, never the donor's. Once the
    sponsorship is confirmed, a note on that contact links the donor, and the
    to-do asks the reviewer to check whether it is the same person. The first
    website of the company with a reviewer is used; without one, only the
    note is left.
- **Payment providers**: the donation checkout embeds the standard Odoo
  `payment.form`; enable and publish the country's `payment.provider` records.
  The checkout brand row (`checkout_payment_brands` anchor in the gift package
  page) shows Mastercard/Visa; country modules inject their local brands there.
- **Dependency note**: `website_legal_page` is an OCA module (OCA/website);
  make sure an OCA/website checkout is on the addons path.

Country-specific behavior (Swiss volunteering features, eBill, local payment
brands, donor-service contact details) lives in the country extension module
(`my_compassion_switzerland` for Switzerland).
