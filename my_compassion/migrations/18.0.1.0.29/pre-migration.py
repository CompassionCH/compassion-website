##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
"""Pre-migration to 18.0.1.0.29 of my_compassion.

The MyCompassion activation and suggested amounts of the donation products
become company-dependent (jsonb ``{company_id: value}``): the values set so far
belong to the product's company, or to the main company for a shared product.
Converted here, as the ORM's own conversion casts the column to jsonb
(``column::jsonb``), which PostgreSQL cannot do from boolean or numeric. The
default of a boolean column (``DEFAULT false``, set by the ORM) is dropped
first: it cannot be cast either, and a company-dependent column has none.
"""

COLUMNS = (
    "activate_for_my_compassion",
    "my_compassion_donation_amount_low",
    "my_compassion_donation_amount_medium",
    "my_compassion_donation_amount_high",
)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "SELECT res_id FROM ir_model_data "
        "WHERE module = 'base' AND name = 'main_company'"
    )
    row = cr.fetchone()
    if not row:
        return
    main_company_id = row[0]
    for column in COLUMNS:
        cr.execute(
            """SELECT data_type FROM information_schema.columns
               WHERE table_name = 'product_template' AND column_name = %s""",
            (column,),
        )
        data_type = (cr.fetchone() or [None])[0]
        if data_type in (None, "jsonb"):
            continue
        # A false/empty value is not stored: the product reads the fallback
        # (data/donation_amount_defaults.xml for the amounts).
        keep = f"{column}" if data_type == "boolean" else f"{column} IS NOT NULL"
        cr.execute(
            f"""ALTER TABLE product_template
                ALTER COLUMN {column} DROP DEFAULT,
                ALTER COLUMN {column} TYPE jsonb
                USING CASE WHEN {keep} THEN jsonb_build_object(
                    COALESCE(company_id, %s)::text, {column}
                ) END""",
            (main_company_id,),
        )
