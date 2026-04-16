from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    if not openupgrade.column_exists(
        env.cr, "product_template", "my_compassion_donation_amount_low"
    ):
        openupgrade.logged_query(
            env.cr,
            """
            ALTER TABLE product_template
            ADD COLUMN my_compassion_donation_amount_low numeric,
            ADD COLUMN my_compassion_donation_amount_medium numeric,
            ADD COLUMN my_compassion_donation_amount_high numeric;
        """,
        )
    openupgrade.logged_query(
        env.cr,
        """
UPDATE product_template
SET
my_compassion_donation_amount_low = my_compassion_donation_quantity_low * list_price,
my_compassion_donation_amount_medium = (
    my_compassion_donation_quantity_medium * list_price),
my_compassion_donation_amount_high = my_compassion_donation_quantity_high * list_price
WHERE my_compassion_donation_amount_low IS NULL;
 """,
    )
