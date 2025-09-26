from openupgradelib import openupgrade


def migrate(cr, version):
    openupgrade.logged_query(
        cr,
        """
        DELETE FROM ir_model_data
            WHERE module = 'my_compassion'
            AND name like 'selection__product_template__my_compassion_pictogram%'
               """,
    )
    openupgrade.logged_query(
        cr,
        """
         DELETE FROM ir_model_data
         WHERE module = 'my_compassion'
           AND name = 'field__product_template__my_compassion_pictogram'
         """,
    )
