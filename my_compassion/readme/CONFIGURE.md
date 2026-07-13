This module is country-agnostic. Each national office deploying it configures:

- **Website record**: `my_compassion.my2_website` ships with a placeholder domain;
  set the real domain and the website languages on the record after install.
- **Company data**: the portal renders the company phone and email
  (donation help blocks, account-deletion help). Set them on the company.
- **Sponsorship products**: the wizard copy renders the monthly amounts of the
  products with `default_code` `sponsorship` and `fund_gen` (the same products
  the contract lines use).
- **System parameters** (optional):
  - `my_compassion.data_change_notification_email`: recipient of the partner
    data-change notifications (defaults to the company email).
  - `my_compassion.sponsor_child_url`: target of the "start a sponsorship"
    link shown to users without sponsorships (defaults to `/my2/children`).
- **Payment providers**: the donation checkout embeds the standard Odoo
  `payment.form`; enable and publish the country's `payment.provider` records.
  The checkout brand row (`checkout_payment_brands` anchor in the gift package
  page) shows Mastercard/Visa; country modules inject their local brands there.
- **Dependency note**: `website_legal_page` is an OCA module (OCA/website);
  make sure an OCA/website checkout is on the addons path.

Country-specific behavior (Swiss volunteering features, eBill, local payment
brands, donor-service contact details) lives in the country extension module
(`my_compassion_switzerland` for Switzerland).
