# Compassion Website · Odoo 18

These addons provide the sponsor portal, public website features and themes. Swiss and
Nordic country addons depend on the portal. The portal also ships Polish translations.

## Dependencies and translations

Declare the addons you use in the manifest's `depends`. Shared website addons can depend
on `compassion-modules` and `compassion-accounting`. Put new country-specific behavior
in a country extension. Existing exceptions include `crowdfunding_compassion` depending
on `partner_communication_switzerland` and Swiss content seeded by older theme
migrations. Use an `auto_install` bridge when an integration should activate whenever
both optional addons are present.

If the module has catalogs, update its existing locales. For its first catalogs,
identify installing countries from country-addon dependencies or deployment
configuration. Ask the maintainer if coverage is unclear. Switzerland uses `fr_CH`,
`de_DE`, `it_IT`. The Nordic countries use `sv_SE`, `nb_NO`, `da_DK`, `fi_FI`. Poland
uses `pl_PL`.

## Where to find the rules

When a task changes code here, open the shared rule subjects it needs. If the toolkit
plugins are available, use their skills `code-rules:rules` and `odoo-rules:rules`;
otherwise fetch the published rules into a temporary folder:
`(d="$(mktemp -d)" && git clone -q --depth 1 --branch main https://github.com/CompassionCH/compassion-agent-toolkit.git "$d" && echo "$d")`.
There, each index is `plugins/<plugin>/skills/rules/SKILL.md`. If the sandbox blocks the
network, ask the user to run the command, or read the indexes online:
[code-rules](https://github.com/CompassionCH/compassion-agent-toolkit/blob/main/plugins/code-rules/skills/rules/SKILL.md)
[odoo-rules](https://github.com/CompassionCH/compassion-agent-toolkit/blob/main/plugins/odoo-rules/skills/rules/SKILL.md)

Read the relevant [architecture decision](docs/adr/) before changing the pattern it
describes. For portal checkout submissions, reuse `sale.order._my2_lock_for_new_payment`
([Order payment guard](my_compassion/models/sale_order.py)).

## Before opening a PR

Run `pre-commit run` on staged files, or `pre-commit install` to enable the hooks on
commit. CI covers static checks only. It runs
`SKIP=oca-gen-addon-readme pre-commit run --all-files --show-diff-on-failure --color=always`
and checks for untracked generated files. Run the affected Odoo tests separately.

Then run the rules review in `review.md`, linked from the code-rules index. Use the
`code-rules:rules-reviewer` subagent when the plugin is available; otherwise give a
fresh read-only session the published reviewer prompt at
`plugins/code-rules/agents/rules-reviewer.md` in that folder. Only if neither is
possible, say in the PR description that no rules review ran. Record findings, coverage
gaps and their disposition there.
