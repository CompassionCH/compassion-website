##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo.tests import tagged

from odoo.addons.website_event_compassion.tests.common import (
    DOWNLOAD_LINK,
    RegistrationCase,
    picture,
)


@tagged("post_install", "-at_install")
class TestRegistrationNotification(RegistrationCase):
    """The Muskathlon registration e-mail links the uploaded picture (T3630)."""

    def notification(self, registration):
        registration.notify_muskathlon_registration()
        return registration.message_ids.filtered(
            lambda m: "Muskathlon" in (m.subject or "")
        )[:1]

    def test_notification_links_the_original(self):
        registration = self.register(profile_picture=picture(4000, 3000))

        self.assertIn(
            DOWNLOAD_LINK.format(id=registration.id),
            self.notification(registration).body,
        )

    def test_notification_without_picture(self):
        registration = self.register()

        self.assertNotIn(
            "profile_picture_original", self.notification(registration).body
        )
