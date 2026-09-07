from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    if version:
        # sbc_compassion's own migration (same upgrade) backfills on_hold on
        # letters already stuck in "Exception" for a benign reason, but runs
        # before my_compassion is loaded, so is_published (defined here)
        # cannot be recomputed there. Do it here instead, now that this
        # module's fields are registered and on_hold is already committed.
        letters = env["correspondence"].search(
            [
                ("state", "=", "Exception"),
                ("on_hold", "=", True),
                ("is_published", "=", False),
            ]
        )
        letters.write({"is_published": True})
