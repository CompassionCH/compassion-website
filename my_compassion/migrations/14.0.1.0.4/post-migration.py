from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    if version:
        # sbc_compassion's own migration (same upgrade) backfills on_hold on
        # letters already stuck in "Exception" for a benign reason, but runs
        # before my_compassion is loaded, so is_published (defined here)
        # cannot be recomputed there. Do it here instead, now that this
        # module's fields are registered and on_hold is already committed.
        # on_hold only ever applies to S2B letters in this compute (the B2S
        # branch has its own, unrelated publication rule), so match its
        # scope exactly here too even though on_hold is not currently set
        # on any B2S letter.
        letters = env["correspondence"].search(
            [
                ("state", "=", "Exception"),
                ("direction", "=", "Supporter To Beneficiary"),
                ("on_hold", "=", True),
                ("is_published", "=", False),
            ]
        )
        letters.write({"is_published": True})
