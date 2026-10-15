# The event of a crowdfunding project and its origins take the campaign of
# the project, which the sponsorships without campaign then take.
from openupgradelib import openupgrade


def migrate(cr, version):
    if not version:
        return
    openupgrade.logged_query(
        cr,
        """
        UPDATE crm_event_compassion e
        SET campaign_id = p.campaign_id
        FROM crowdfunding_project p
        WHERE p.event_id = e.id AND e.campaign_id IS NULL
        """,
    )
    openupgrade.logged_query(
        cr,
        """
        UPDATE recurring_contract_origin o
        SET campaign_id = p.campaign_id
        FROM crowdfunding_project p
        WHERE p.event_id = o.event_id AND o.campaign_id IS NULL
        """,
    )
    openupgrade.logged_query(
        cr,
        """
        UPDATE recurring_contract c
        SET campaign_id = o.campaign_id
        FROM recurring_contract_origin o
        WHERE o.id = c.origin_id
            AND o.campaign_id IS NOT NULL
            AND c.campaign_id IS NULL
        """,
    )
