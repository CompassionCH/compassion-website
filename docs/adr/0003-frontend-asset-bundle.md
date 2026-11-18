# Bundle ordinary frontend assets across website pages

Declare website and portal JavaScript, client templates and CSS in the manifest's
`web.assets_frontend`, including styles used on just one page. Scope feature styles to
their page or component. Server-rendered QWeb views load through the manifest's `data`.
[Portal manifest](../../my_compassion/__manifest__.py)

The first visit loads some code meant for other pages. Later pages reuse the versioned
bundle and its registered widgets and templates. Page-scoped bundles would make each
page responsible for loading its dependencies. Inline stylesheet links bypass the
bundle's versioned URL.

Some pages, including the dashboard and login, still link CSS inline. When changing a
page with an inline stylesheet, include its move to the bundle in that PR and mention it
in the description. Before bundling, check every selector against other templates and
theme styles. Scope collisions to the intended page first. For example, the login
stylesheet sets `.single-column` to 300px, and other portal pages use that same class.
Remove the inline link once the scoped stylesheet is bundled.
[Login stylesheet](../../my_compassion/static/src/css/my2_login.css) ·
[Another portal page](../../my_compassion/templates/pages/my2_children.xml)

Load a large dependency used by a single feature when that feature starts. For example,
the map widget belongs in the frontend bundle and loads the external map SDK when it
mounts. [Map widget](../../theme_compassion_2025/static/src/js/widgets/map.js)
