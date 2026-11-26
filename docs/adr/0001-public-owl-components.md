# Mount reusable public controls as Owl components

The theme exposes reusable controls through module-qualified names in
`public_components` and declared props. For a control present in server-rendered QWeb
with JSON props, use `<owl-component>`. The login page embeds the password control this
way and needs no initialization code.
[Password component](../../theme_compassion_2025/static/src/js/components/Password.js) ·
[Login template](../../my_compassion/templates/pages/my2_login_template.xml)

Use `mountComponent` with the existing `Component.env` when the page supplies a callback
or owns the control's runtime lifecycle. The range slider takes a function prop. The
letter page mounts its progress bar when the modal opens and keeps the app handle to
destroy it on error, even though its props are JSON values. Sharing the environment
avoids starting page services twice. Selector-based snippets can still use
`publicWidget`. [Slider mount](../../my_compassion/static/src/js/my2_sponsorships.js) ·
[Letter progress bar](../../my_compassion/static/src/js/my2_new_letter.js)
