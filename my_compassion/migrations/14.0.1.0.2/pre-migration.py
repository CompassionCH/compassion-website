from openupgradelib import openupgrade


# Specific Product IDs (Production Database)
PRODUCT_ID_SURVIVAL = 15
PRODUCT_ID_CHRISTMAS = 31
PRODUCT_ID_UNSPONSORED_CHILD = 39
PRODUCT_ID_WASH = 41
PRODUCT_ID_DISASTER = 238
PRODUCT_ID_FOOD = 303
PRODUCT_ID_HEALTH = 474

# Full list of products targeted by the migration
TARGET_PRODUCT_IDS = (
    PRODUCT_ID_SURVIVAL,
    PRODUCT_ID_CHRISTMAS,
    PRODUCT_ID_UNSPONSORED_CHILD,
    PRODUCT_ID_WASH,
    PRODUCT_ID_DISASTER,
    PRODUCT_ID_FOOD,
    PRODUCT_ID_HEALTH,
)

@openupgrade.migrate()
def migrate(env, version):
    """
    Pre-migration script for 14.0.1.0.2.

    Set and modify XML_ID of some product.template:
    - Health funds product (ID 474) was without xml_id
      -> assigned 'product_template_fund_hea'
    - Food aid program product (ID 303) had an id of type '__export__.'
      -> renamed to 'product_template_fund_fda'
    - Emergency funds product (ID 238) had an id of type '__export__.'
      -> renamed to 'product_template_fund_dis'

    Remove old translations:
    - We delete entries in ir_translation for name and description.
    - Reason: Odoo protects existing translations. Deleting them forces Odoo
      to reload fresh translations from the .po files during the XML update.

    Clean One2many lines (Impact & Info):
    - We clear donation.impact.line and donation.info.line tables.
    - Reason: Moving from 'anonymous' lines (created via (0,0)) to
      'named' lines (XML records) requires a clean slate to avoid duplications.
    """
    cr = env.cr

    # -------------------------------------------------------------------------
    # XML_IDS MANAGEMENT
    # -------------------------------------------------------------------------

    # Add missing XML_ID for Health product
    openupgrade.add_xmlid(
        cr,
        "my_compassion",
        "product_template_fund_hea",
        "product.template",
        PRODUCT_ID_HEALTH,
        noupdate=False,
    )

    # Rename old "__export__" IDs to proper module IDs
    xml_id_mapping = {
        PRODUCT_ID_DISASTER: "product_template_fund_dis",
        PRODUCT_ID_FOOD: "product_template_fund_fda",
    }

    for res_id, new_name in xml_id_mapping.items():
        cr.execute(
            "SELECT module, name FROM ir_model_data WHERE model = %s AND res_id = %s",
            ("product.template", res_id),
        )
        res = cr.fetchone()

        if res:
            old_module, old_name = res
            openupgrade.rename_xmlids(
                cr, [(f"{old_module}.{old_name}", f"my_compassion.{new_name}")]
            )

    # -------------------------------------------------------------------------
    # CLEANUP OLD TRANSLATIONS
    # -------------------------------------------------------------------------

    # Force Odoo to reload translations from .po file by removing existing ones
    # for the targeted products only.
    cr.execute(
        """
        DELETE FROM ir_translation
        WHERE name IN ('product.template,my_compassion_name',
                       'product.template,my_compassion_description')
        AND res_id IN %s
        """,
        (TARGET_PRODUCT_IDS,),
    )

    # -------------------------------------------------------------------------
    # CLEANUP ONE2MANY LINES
    # -------------------------------------------------------------------------

    # Cleanup Impact Lines
    # Applies to all products EXCEPT Christmas Gift (which does not use this model)
    impact_ids_to_clean = tuple(
        pid for pid in TARGET_PRODUCT_IDS if pid != PRODUCT_ID_CHRISTMAS
    )

    if impact_ids_to_clean:
        cr.execute(
            "DELETE FROM donation_impact_line WHERE donation_id IN %s",
            (impact_ids_to_clean,),
        )

    # Cleanup Info Lines
    # Applies ONLY to Christmas Gift product
    cr.execute(
        "DELETE FROM donation_info_line WHERE donation_id = %s",
        (PRODUCT_ID_CHRISTMAS,)
    )
