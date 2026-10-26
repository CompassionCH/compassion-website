from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    """Drop the public read rule on registrations (T3569).

    It let anyone read every field of a published registration, passport
    included. Declared noupdate, so removing it from the XML is not enough.
    """
    rule = env.ref(
        "muskathlon.muskathlon_registration_public", raise_if_not_found=False
    )
    if rule:
        rule.unlink()
