from openupgradelib import openupgrade

group_visit_data = [
    # Add tuples with the XML ID names, model names, and database IDs for "Group Visit"
    # ("xml_id_name", "model.name", database_id),
    # ...
]

def migrate(cr, version):
    for data in group_visit_data:
        openupgrade.add_xmlid(
            cr, "your_module_name", data[0], data[1], data[2], noupdate=False
        )