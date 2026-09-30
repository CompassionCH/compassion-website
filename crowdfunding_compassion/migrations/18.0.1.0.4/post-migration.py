# ruff: noqa: E501 -- email template HTML, kept on one line per paragraph
import json

from openupgradelib import openupgrade

# The TOGETHER donation templates only live in the database (the XML holds a
# placeholder, noupdate). The v14 -> v18 conversion kept Jinja in them: a
# "| int" filter that makes the donation receipt fail, and German, French and
# Italian texts never converted (in some, even the Jinja code was translated).
# Rewrite them in QWeb, keeping their wording.

DONOR_VARS = """<t t-set="invoice" t-value="object.get_objects()"/>
<t t-set="projects" t-value="invoice.mapped('invoice_line_ids.crowdfunding_participant_id.project_id')"/>
<t t-set="project_names" t-value="', '.join(projects.mapped('name'))"/>
<t t-set="partner" t-value="object.partner_id"/>
<t t-set="plural" t-value="partner.title.plural or partner.title.id == 29"/>
<t t-set="total" t-value="sum(invoice.mapped('amount_total'))"/>
<t t-set="amount" t-value="'%d' % total if total == int(total) else '%.2f' % total"/>
"""

DONATION_SUCCESSFUL_BODY = {
    "en_US": DONOR_VARS
    + """<div>
<t t-out="partner.informal_salutation"/><br/><br/>
We thank you for the donation of CHF <t t-out="amount"/> you made for the project <t t-out="project_names"/>.<br/><br/>
Your generosity will help release more children from extreme poverty, by giving them a better future. This is marvelous! Together, let's change the world, step by step.<br/><br/>
The Together team of Compassion Switzerland
</div>""",
    "fr_CH": DONOR_VARS
    + """<div>
<t t-out="partner.informal_salutation"/><br/><br/>
Un grand merci pour le don de CHF <t t-out="amount"/> que <t t-out="'vous avez' if plural else 'tu as'"/> versé au projet <t t-out="project_names"/>.<br/><br/>
Cet élan de générosité permettra de libérer encore davantage d'enfants de l'extrême pauvreté, en leur offrant un avenir meilleur. Formidable! Ensemble, changeons le monde, pas à pas.<br/><br/>
L'équipe TOGETHER de Compassion
</div>""",
    "it_IT": DONOR_VARS
    + """<div>
<t t-out="partner.informal_salutation"/><br/><br/>
Grazie mille per la donazione di CHF <t t-out="amount"/> che hai versato in favore del progetto <t t-out="project_names"/>.<br/><br/>
Questa tua generosità contribuirà a liberare ancora più bambini dall'estrema povertà e a dare loro un futuro migliore. È fantastico! Insieme, cambiamo il mondo, passo dopo passo.<br/><br/>
Il team Together di Compassion Svizzera.
</div>""",
    "de_DE": DONOR_VARS
    + """<t t-set="big" t-value="total &gt;= 1000"/>
<t t-set="deine" t-value="'Ihre' if big else ('eure' if plural else 'deine')"/>
<t t-set="dein" t-value="'Ihr' if big else ('euer' if plural else 'dein')"/>
<t t-set="lass" t-value="'Lassen Sie' if big else ('Lasst' if plural else 'Lass')"/>
<t t-set="number_fcps" t-value="object.get_snippet('number_fcps', strip_html=True)"/>
<t t-set="number_children" t-value="object.get_snippet('number_children', strip_html=True)"/>
<p><t t-out="partner.salutation"/></p>
<p>Vielen Dank für <t t-out="deine"/> Spende von CHF <t t-out="amount"/> für das Projekt <t t-out="project_names"/>.</p>
<p>Dank <t t-out="deine"/>m Engagement und dem Einsatz unserer rund <t t-out="number_fcps"/> Partnerkirchen vor Ort unterstützen wir zurzeit <t t-out="number_children"/> Millionen Kinder im globalen Süden. Gemeinsam tun wir das mit einem Ziel: sie nachhaltig aus Armut zu befreien.</p>
<p>Mit <t t-out="deine"/>r Spende können noch mehr Kinder aus Armut befreit werden und Menschen eine bessere Zukunft ermöglicht werden – das ist ein Grund zum Feiern! <t t-out="lass"/> uns die Welt verändern, Schritt für Schritt – zusammen.</p>
<p><t t-out="dein.title()"/> «TOGETHER»-Team von Compassion</p>""",
}

DONATION_SUCCESSFUL_SUBJECT = {
    "en_US": "Thank you for your generous donation!",
    "fr_CH": "Merci pour {{ 'votre' if object.partner_id.title.plural "
    "or object.partner_id.title.id == 29 else 'ton' }} généreux don!",
    "it_IT": "Grazie per la tua generosa donazione!",
    "de_DE": "Danke für {{ 'Ihre' if sum(object.get_objects().mapped('amount_total')) "
    ">= 1000 else ('eure' if object.partner_id.title.plural "
    "or object.partner_id.title.id == 29 else 'deine') }} Spende!",
}

RECEIVED_VARS = """<t t-set="donations" t-value="object.get_objects()"/>
<t t-set="project" t-value="donations.mapped('crowdfunding_participant_id.project_id')[:1]"/>
<t t-set="partner" t-value="object.partner_id"/>
<t t-set="donor" t-value="donations.mapped('move_id.partner_id')[:1]"/>
<t t-set="anonymous" t-value="donations[:1].is_anonymous"/>
<t t-set="total" t-value="sum(donations.mapped('price_total'))"/>
<t t-set="amount" t-value="'%d' % total if total == int(total) else '%.2f' % total"/>
"""


def _received_body(intro, from_word, text, together, link_label, team, after=""):
    return (
        RECEIVED_VARS
        + f"""<div>
<t t-out="partner.informal_salutation"/><br/><br/>
{intro} CHF <t t-out="amount"/><t t-if="not anonymous"> {from_word} <t t-out="donor.name"/><t t-if="donor.email"> (<t t-out="donor.email"/>)</t></t>{after}. {text}<br/><br/>
{together}<br/><br/>
<t t-if="project"><p><a t-attf-href="{{{{ project.get_base_url() }}}}{{{{ project.website_url }}}}">{link_label}</a></p></t>
{team}<br/>
</div>"""
    )


DONATION_RECEIVED_BODY = {
    "en_US": _received_body(
        "Let's celebrate! You just received a donation of",
        "from",
        "What a great news. You are one step closer to your goal. We share the joy "
        "to know that thanks to your efforts, more children living in extreme "
        "poverty can be helped.",
        "Together, we want to change the world, one child at a time.",
        "View your project",
        "The Together team of Compassion Switzerland",
    ),
    "de_DE": _received_body(
        "Lass uns feiern! Du hast soeben eine Spende von",
        "von",
        "Was für eine tolle Nachricht. Du bist deinem Ziel einen Schritt näher "
        "gekommen. Wir freuen uns mit dir, dass dank deines Einsatzes mehr Kindern, "
        "die in extremer Armut leben, geholfen werden kann.",
        "Gemeinsam wollen wir die Welt verändern, ein Kind nach dem anderen.",
        "Zu deinem Projekt",
        "Das Together-Team von Compassion Schweiz",
        after=" erhalten",
    ),
    "fr_CH": _received_body(
        "C'est la fête ! Vous venez de recevoir un don de",
        "de la part de",
        "Quelle bonne nouvelle ! Vous avez fait un pas de plus vers votre objectif. "
        "Nous partageons la joie de savoir que grâce à vos efforts, davantage "
        "d'enfants vivant dans l'extrême pauvreté peuvent être aidés.",
        "Ensemble, nous voulons changer le monde, un enfant à la fois.",
        "Voir votre projet",
        "L'équipe TOGETHER de Compassion Suisse",
    ),
    "it_IT": _received_body(
        "Festeggiamo! Hai appena ricevuto una donazione di",
        "da",
        "Che bella notizia! Sei un passo più vicino al tuo obiettivo. Condividiamo "
        "la gioia di sapere che grazie ai tuoi sforzi, altri bambini che vivono in "
        "condizioni di estrema povertà potranno essere aiutati.",
        "Insieme vogliamo cambiare il mondo, un bambino alla volta.",
        "Vedi il tuo progetto",
        "Il team Together di Compassion Svizzera",
    ),
}

DONATION_RECEIVED_SUBJECT = {
    "en_US": "You received a donation",
    "de_DE": "Du hast eine Spende erhalten!",
    "fr_CH": "Vous avez reçu un don !",
    "it_IT": "Hai ricevuto una donazione!",
}


@openupgrade.migrate()
def migrate(env, version):
    for xmlid, body, subject in (
        (
            "crowdfunding_compassion.donation_successful_email_template",
            DONATION_SUCCESSFUL_BODY,
            DONATION_SUCCESSFUL_SUBJECT,
        ),
        (
            "crowdfunding_compassion.donation_received_email_template",
            DONATION_RECEIVED_BODY,
            DONATION_RECEIVED_SUBJECT,
        ),
    ):
        template = env.ref(xmlid, raise_if_not_found=False)
        if template:
            env.cr.execute(
                "UPDATE mail_template SET body_html = %s, subject = %s WHERE id = %s",
                (json.dumps(body), json.dumps(subject), template.id),
            )
    env["mail.template"].invalidate_model(["body_html", "subject"])
