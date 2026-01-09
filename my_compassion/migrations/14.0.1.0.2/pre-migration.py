from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    """
        Pre-migration script for 14.0.1.0.2.
        Set and modify XML_ID of some product.template.
            - Health funds product were without xml_id
                -> 'product_template_fund_hea'
            - Food aid program produt had an id of type '__export__.'
                -> 'product_template_fund_fda'
            - Emergency funds product had an id of type '__export__.'
                -> 'product_template_fund_dis'
        """
    cr = env.cr

    # Standard processing for ID 474 (did not have an XML ID)
    openupgrade.add_xmlid(
        cr, "my_compassion", "product_template_fund_hea",
        "product.template", 474, noupdate=False
    )

    # Handling existing IDs of type “__export__.” (238 and 303)
    # We define the mapping { res_id: ‘new_name’ }
    mapping = {
        238: "product_template_fund_dis",
        303: "product_template_fund_fda",
    }

    for res_id, new_name in mapping.items():
        cr.execute(
            "SELECT module, name FROM ir_model_data WHERE model = %s AND res_id = %s",
            ('product.template', res_id)
        )
        res = cr.fetchone()

        if res:
            old_module, old_name = res
            openupgrade.rename_xmlids(cr, [
                (
                    f"{old_module}.{old_name}",
                    f"my_compassion.{new_name}"
                )
            ])
