# ruff: noqa: E501 -- email template HTML, kept on one line per paragraph
import json

from openupgradelib import openupgrade

# The project emails are about one project: a new project must not be merged
# into a pending email of the same owner (the templates then fail with
# several projects). "Project published" and "Project joined" still had
# Jinja in German, French and Italian after the v14 -> v18 conversion.

PROJECT_VARS = """<t t-set="project" t-value="object.get_objects()[:1]"/>
<t t-set="partner" t-value="object.partner_id"/>
<t t-set="project_url" t-value="project.get_base_url() + project.website_url"/>
"""

PUBLISHED_BODY = {
    "en_US": PROJECT_VARS
    + """<div>
<t t-out="partner.informal_salutation"/><br/><br/>
Great news! Your project <t t-out="project.name"/> is now active on Together. Thanks to your project, more children will be released from extreme poverty.<br/><br/>
You can start fundraising or motivate your network to sponsor a child. You just can share <a t-att-href="project_url">the link of your project</a> to invite people to join you in your efforts to change the world.<br/><br/>
We wish you great success in your adventure!<br/><br/>
The Together team of Compassion Switzerland
</div>""",
    "de_DE": PROJECT_VARS
    + """<div>
<t t-out="partner.informal_salutation"/><br/><br/>
Es ist soweit, dein grossartiges Projekt <span style="text-decoration: underline;"><t t-out="project.name"/></span> ist nun auf unserer Plattform aktiviert - ein Grund zum Feiern! Wir freuen uns mit dir, dass mithilfe deines Projektes noch mehr Kinder aus Armut befreit werden und Menschen eine bessere Zukunft erhalten.<br/><br/>
Du kannst ab sofort mit Spenden sammeln und/oder Patenschaften vermitteln beginnen. Schicke deinen Freunden und Bekannten <a t-att-href="project_url">den Link deines Projektes</a> und lade sie ein, mit dir zusammen die Welt zu verändern, indem sie für dein Projekt spenden oder eine Patenschaft übernehmen. Unser Plattformname «TOGETHER» bedeutet, dass wir zusammen, ensemble, insieme, Hoffnung bringen. Let’s start!<br/><br/>
Wir wünschen dir mit deinem Projekt-Abenteuer viele ermutigende und spannende Momente!<br/><br/>
Dein «TOGETHER»-Team von Compassion Schweiz
</div>""",
    "fr_CH": PROJECT_VARS
    + """<div>
<t t-out="partner.informal_salutation"/>,<br/><br/>
Ça y est, ton projet <span style="text-decoration: underline;"><t t-out="project.name"/></span> est désormais activé sur TOGETHER. C'est la fête: grâce à ton projet, toujours plus d'enfants vont pouvoir être libérés de la pauvreté, pour un avenir meilleur.<br/><br/>
C'est parti! Dès à présent, tu peux commencer à récolter des fonds ou motiver ton entourage à parrainer un enfant démuni. Pratiquement, il te suffit d'envoyer <a t-att-href="project_url">le lien de ton projet</a> avec une invitation à se joindre à toi pour rendre le monde meilleur.<br/><br/>
TOGETHER: le nom de notre plateforme est clair. Ensemble, zusammen, insieme, nous pouvons apporter de l'espoir dans les vies les plus désespérées.<br/><br/>
Nous te souhaitons de nombreux moments encourageants, surprenants et passionnants à travers l'aventure de ce projet.<br/><br/>
L'équipe TOGETHER de Compassion.
</div>""",
    "it_IT": PROJECT_VARS
    + """<div>
<t t-out="partner.informal_salutation"/>,<br/><br/>
Il tuo grande progetto <span style="text-decoration: underline;"><t t-out="project.name"/></span> è ora attivo su TOGETHER. Grazie a te e alla tua idea, sempre più bambini saranno liberati dalla povertà e avranno un futuro migliore.<br/><br/>
Cominciamo! Da ora puoi iniziare la raccolta di fondi o motivare amici, famiglia e perchè no colleghi o compagni di classe a sostenere un bambino in difficoltà. In pratica, tutto quello che dovrai fare è inviare <a t-att-href="project_url">il link del tuo progetto</a> con un invito ad unirti a te e alla tua sfida, per rendere il mondo un posto migliore.<br/><br/>
TOGETHER: il nome della nostra piattaforma è chiaro. Insieme, zusammen, ensemble, possiamo portare speranza alle vite più disperate.<br/><br/>
Ti auguriamo tanti momenti incoraggianti, sorprendenti ed emozionanti attraverso questa avventura.<br/><br/>
Il team TOGETHER di Compassion Svizzera.
</div>""",
}

JOINED_BODY = {
    "en_US": PROJECT_VARS
    + """<div>
<t t-out="partner.informal_salutation"/><br/><br/>
You joined the project <t t-out="project.name"/>. Amazing! Thanks to this project, more children will be released from extreme poverty.<br/><br/>
In order to manage your project, you can use your Compassion login on the platform. If you don't have an account, you will get it in a separate e-mail. In case you have more questions, don't hesitate to write to us at together@compassion.ch<br/><br/>
Thank you for your commitment to release more children from extreme poverty. Before the start of your project, we send you our best greetings and encouragements for your fundraising.<br/><br/>
The Together team of Compassion Switzerland
</div>""",
    "de_DE": PROJECT_VARS
    + """<div>
<t t-out="partner.informal_salutation"/><br/><br/>
Du hast dich erfolgreich dem Projekt <t t-out="project.name"/> angeschlossen. Wir freuen uns mit dir, dass mithilfe dieses Projektes noch mehr Kinder aus Armut befreit werden und Menschen eine bessere Zukunft erhalten – das ist ein Grund zum Feiern!<br/><br/>
Für dieses Projekt gilt dein bereits bestehendes Login von Compassion. Wenn du noch kein Login hast, wird dir dieses in einer separaten Mail zugeschickt. Falls du diesbezüglich Probleme oder Fragen hast, melde dich per Mail bei together@compassion.ch.<br/><br/>
Du kannst ab sofort mit Spenden sammeln und/oder Patenschaften vermitteln beginnen. Schicke deinen Freunden und Bekannten <a t-att-href="project_url">den Link deines Projektes</a> und lade sie ein, mit dir zusammen die Welt zu verändern, indem sie für dein Projekt spenden oder eine Patenschaft für ein Kind in extremer Armut übernehmen. Unser Plattformname «together» bedeutet, dass wir zusammen, ensemble, insieme, Hoffnung in hoffnungslose Leben bringen. Let’s start!<br/><br/>
Wir wünschen dir mit diesem Projekt-Abenteuer viele ermutigende, spannende, lohnende, erstaunliche Momente!<br/><br/>
Dein «together»-Team von Compassion Schweiz
</div>""",
    "fr_CH": PROJECT_VARS
    + """<t t-set="plural" t-value="partner.title.plural or partner.title.id == 29"/>
<t t-set="tu" t-value="'vous' if plural else 'tu'"/>
<t t-set="te" t-value="'vous' if plural else 'te'"/>
<t t-set="ton" t-value="'votre' if plural else 'ton'"/>
<t t-set="toi" t-value="'vous' if plural else 'toi'"/>
<div>
<t t-out="partner.informal_salutation"/>,<br/><br/>
<t t-out="'Vous avez' if plural else 'Tu as'"/> rejoint avec succès le projet <t t-out="project.name"/>. C'est formidable: grâce à ce projet, toujours plus d'enfants vont pouvoir être libérés de la pauvreté pour un avenir meilleur.<br/><br/>
Pour suivre et gérer ce projet, il <t t-out="te"/> suffit d'utiliser <t t-out="ton"/> Login de Compassion. Si <t t-out="tu"/> n'en <t t-out="'avez' if plural else 'as'"/> pas encore, il <t t-out="te"/> sera envoyé dans un mail séparé. En cas de problèmes ou de questions relatifs à cet accès, n'hésite<t t-out="'z' if plural else ''"/> pas à prendre contact avec together@compassion.ch.<br/><br/>
C'est parti! Dès à présent, <t t-out="'vous pouvez' if plural else 'tu peux'"/> commencer à récolter des fonds ou motiver <t t-out="ton"/> entourage à parrainer un enfant démuni. Pratiquement, il <t t-out="te"/> suffit d'envoyer <a t-att-href="project_url">le lien de <t t-out="ton"/> projet</a> avec une invitation à se joindre à <t t-out="toi"/> pour rendre le monde meilleur.<br/><br/>
Together: le nom de notre plateforme est clair. Ensemble, zusammen, insieme, nous pouvons apporter de l'espoir dans les vies les plus désespérées.<br/><br/>
Nous <t t-out="te"/> souhaitons de nombreux moments encourageants, surprenants et passionnants à travers l'aventure de ce projet.<br/><br/>
L'équipe TOGETHER de Compassion.
</div>""",
    "it_IT": PROJECT_VARS
    + """<div>
<t t-out="partner.informal_salutation"/><br/><br/>
Hai aderito con successo al progetto <t t-out="project.name"/>. È fantastico: grazie a questa tua iniziativa, sempre più bambini potranno essere liberati dalla povertà per un futuro migliore.<br/><br/>
Per seguire e gestire questo progetto, tutto quello che devi fare è usare il tuo Compassion Account. Se non ne hai ancora uno, te lo invieremo in un'e-mail separata. In caso di problemi o domande relative a questo accesso, non esitare a contattare together@compassion.ch.<br/><br/>
Cominciamo! Da ora, potrai iniziare la raccolta di fondi o motivare amici, famiglia, perchè no colleghi e compagni di scuola forse? A sostenere un bambino in difficoltà. In pratica, tutto quello che dovrai fare è inviare <a t-att-href="project_url">il link del tuo progetto</a> ed invitare i tuoi contatti a rendere il mondo un posto migliore.<br/><br/>
Together: il nome della nostra piattaforma è chiaro. Insieme, zusammen, ensemble, possiamo portare speranza alle vite più disperate.<br/><br/>
Ti auguriamo tanti momenti incoraggianti, sorprendenti ed emozionanti attraverso questa avventura!<br/><br/>
Il team Together di Compassion Svizzera.
</div>""",
}


@openupgrade.migrate()
def migrate(env, version):
    configs = env["partner.communication.config"]
    for xmlid in (
        "crowdfunding_compassion.config_project_confirmation",
        "crowdfunding_compassion.config_project_join",
        "crowdfunding_compassion.config_project_published",
    ):
        configs |= env.ref(xmlid, raise_if_not_found=False) or configs
    configs.write({"forbid_merging": True})

    for xmlid, body in (
        ("crowdfunding_compassion.project_published_email_template", PUBLISHED_BODY),
        ("crowdfunding_compassion.project_join", JOINED_BODY),
    ):
        template = env.ref(xmlid, raise_if_not_found=False)
        if template:
            env.cr.execute(
                "UPDATE mail_template SET body_html = %s WHERE id = %s",
                (json.dumps(body), template.id),
            )

    # Project creation confirmation: French subject with the forms of address
    # swapped, and a typo in the French text.
    template = env.ref(
        "crowdfunding_compassion.project_confirmation_email_template",
        raise_if_not_found=False,
    )
    if template:
        env.cr.execute(
            """
            UPDATE mail_template
            SET subject = jsonb_set(subject, '{fr_CH}', to_jsonb(%s::text)),
                body_html = jsonb_set(body_html, '{fr_CH}', to_jsonb(
                    replace(body_html->>'fr_CH', 'pourra être activité', 'pourra être activé')))
            WHERE id = %s AND subject ? 'fr_CH' AND body_html ? 'fr_CH'
            """,
            (
                "{{ 'Vous y êtes presque!' if object.partner_id.title.plural "
                "or object.partner_id.title.id == 29 else 'Tu y es presque!' }}",
                template.id,
            ),
        )
    env["mail.template"].invalidate_model(["body_html", "subject"])
