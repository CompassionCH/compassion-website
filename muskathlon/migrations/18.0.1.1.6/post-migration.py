from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    """The Muskathlon registrations wait in Fill documents: the person
    responsible moves them to Criminal record (T3523). The stages are
    noupdate."""
    env.ref("muskathlon.stage_criminal_record").manual_only = True
