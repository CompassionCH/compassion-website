This module is `auto_install`: Odoo installs it on its own only in the run
that installs one of its dependencies, `my_compassion` or
`payment_payu_gpo`. On a database that has both before this module is
deployed, install it explicitly, e.g. `-i my_compassion_payment_payu_gpo`:
updating `my_compassion` (`-u`) does not install it.
