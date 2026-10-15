# ruff: noqa: E501
##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
"""Post-migration to 18.0.1.1.1 of muskathlon.

The donation notification template is noupdate and its stored body was
broken after the v18 migration (corrupted donor link, unknown field
``thankyou_letter`` in German, ``t-else`` / ``<ul>`` mismatch). Override the
English body and the German translation in the database.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

BODY_EN = """<div>
                    <t t-set="invoice_lines" t-value="object.get_objects()"/>
                    <t t-set="donations" t-value="invoice_lines.get_donations()"/>
                    <t t-set="partner" t-value="object.partner_id"/>
                    <t t-set="donors" t-value="invoice_lines.mapped(&#x27;partner_id&#x27;)"/>
                    <t t-set="muskathlon" t-value="partner.registration_ids[:1]"/>
                </div>
                <div>
                    <t t-out="partner.salutation"></t>,
                    <br/>
                    <br/>
                    Compassion is glad to inform you that you just received a donation of <t t-out="donations[0]"></t>.-
                    <t t-if="donations[1]">
                        for the <t t-out="donations[1]"></t>.
                    </t>
                    <br/>
                    <br/>
                    <t t-if="len(donors) == 1">
                        Your donor is <t t-out="donors.preferred_name"></t> from <t t-out="donors.city"></t>.
                        <t t-if="donors.email and donors.thankyou_preference != &#x27;none&#x27;">
                    You can personally thank <t t-out="donors.get(&#x27;him&#x27;)"></t> if you wish by sending <t t-out="donors.get(&#x27;him&#x27;)"></t> an e-mail at <a t-attf-href="mailto:{{donors.email}}" style="text-decoration:none;background-color:transparent;color:rgb(124, 123, 173);"><t t-out="donors.email"></t></a>. In any case, <t t-out="donors.get(&#x27;he&#x27;)"></t> will receive a thank you letter from us.
                        </t>
                    </t>
<t t-else="">
                        You received this from the following people. You may contact them by e-mail if you wish to thank them personally.
                        <ul style="margin:0px 0 1rem 0;">
                            <t t-foreach="donors" t-as="donor">
                            <li>
                                <t t-out="donor.preferred_name"/> from <t t-out="donor.city"/>
                                <t t-if="donor.email and donor.thankyou_preference != 'none'">
                                    (<a t-attf-href="mailto:{{donor.email}}" style="text-decoration:none;background-color:transparent;color:rgb(124, 123, 173);"><t t-out="donor.email"/></a>)
                                </t>
                            </li>
                            </t>
                        </ul>
                    </t>
                    <t t-if="muskathlon">
                        You currently have raised <t t-out="object.user_id.company_id.currency_id.symbol"></t> <t t-out="muskathlon.amount_raised"></t>.- You can check your barometer at anytime
                        <a t-attf-href="{{muskathlon.website_url}}" style="text-decoration:none;background-color:transparent;color:rgb(124, 123, 173);">on your sport profile page</a>.
                    </t>
                    <br/>
                    <br/>
                    Yours sincerely
                </div>

"""

BODY_DE = """<div>
    <t t-set="invoice_lines" t-value="object.get_objects()"/>
    <t t-set="donations" t-value="invoice_lines.get_donations()"/>
    <t t-set="partner" t-value="object.partner_id"/>
    <t t-set="plural" t-value="partner.title.plural or partner.title.id == 29"/>
    <t t-set="du" t-value="'ihr' if plural else 'du'"/>
    <t t-set="dir" t-value="'euch' if plural else 'dir'"/>
    <t t-set="dich" t-value="'euch' if plural else 'dich'"/>
    <t t-set="dein" t-value="'euer' if plural else 'dein'"/>
    <t t-set="deine" t-value="'eure' if plural else 'deine'"/>
    <t t-set="donors" t-value="invoice_lines.mapped('partner_id')"/>
    <t t-set="muskathlon" t-value="partner.registration_ids[:1]"/>
    <t t-set="url" t-value="muskathlon.host_url + (muskathlon.website_url or '')"/>
    <t t-set="amount_raised" t-value="'{:.0f}.-'.format(muskathlon.amount_raised or 0.0)"/>
</div>
<p>
    <t t-out="partner.salutation"/>
</p>
<p>
    Wir freuen uns, <t t-out="dir"/> mitzuteilen, dass <t t-out="du"/> gerade eine Spende von <t t-out="donations[0]"/> erhalten <t t-out="&quot;habt&quot; if&#10;    plural else &quot;hast&quot;"/>.
</p>
<t t-if="len(donors) == 1">
    <t t-out="donors.preferred_name"/> aus <t t-out="donors.city"/> <t t-out="donors.get('has')"/> für <t t-out="dich"/> gespendet.

    <t t-if="donors.email and donors.thankyou_preference != 'none'">
        <t t-out="&quot;Ihr könnt&quot; if plural else &quot;Du kannst&quot;"/> <t t-out="donors.get('ihm')"/> persönlich danken (<a t-attf-href="mailto:{{donors.email}}"><t t-out="donors.email"/></a>). <t t-out="donors.get('he').title()"/> <t t-out="donors.get('will be')"/> auch von Compassion einen Dankesbrief erhalten.
    </t>
</t>
<t t-else="">
    <p>
        Die Spenden stammen von den folgenden Personen. <t t-out="&quot;Ihr könnt&quot; if plural else &quot;Du kannst&quot;"/> sie per E-Mail kontaktieren, um <t t-out="dich"/> persönlich zu bedanken.
    </p>
    <ul>
        <t t-foreach="donors" t-as="donor">
            <t t-set="email" t-value="donor.thankyou_preference != 'none' and donor.email"/>
            <li>
                <t t-out="donor.preferred_name"/> aus <t t-out="donor.city"/>
                <t t-if="email">
                    (<a t-attf-href="mailto:{{donor.email}}"><t t-out="donor.email"/></a>)
                </t>
            </li>
        </t>
    </ul>
</t>

<p>
    <t t-out="&quot;Ihr habt&quot; if plural else &quot;Du hast&quot;"/> bereits CHF <t t-out="amount_raised"/> gesammelt. <t t-out="dein.title()"/> Barometer
    <t t-out="&quot;könnt ihr&quot; if plural else &quot;kannst du&quot;"/> jederzeit in
    <a t-attf-href="{{url}}">
        <t t-out="deine"/>m Profil einsehen.
    </a>
</p>
<p>
    Wir wünschen <t t-out="dir"/> alles Gute bei den weiteren Vorbereitungen und beim Training für den Muskathlon. Danke für
    <t t-out="deine"/>n extremen Einsatz gegen extreme Armut!
</p>
<p>
    Herzliche Grüsse vom Compassion Team
</p>
"""


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    template = env.ref(
        "muskathlon.ambassador_donation_confirmation_template",
        raise_if_not_found=False,
    )
    if not template:
        return

    template.with_context(lang="en_US").body_html = BODY_EN
    german_langs = env["res.lang"].search([("code", "=like", "de\\_%")])
    for lang in german_langs.mapped("code"):
        template.with_context(lang=lang).body_html = BODY_DE
    _logger.info(
        "overrode the muskathlon donation notification template (en_US, %s)",
        ", ".join(german_langs.mapped("code")),
    )
