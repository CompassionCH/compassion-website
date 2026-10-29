##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import base64
import io

from PIL import Image

from odoo.tests import TransactionCase


def picture(width, height, image_format="JPEG"):
    """A plain picture, as base64, of the given size."""
    content = io.BytesIO()
    Image.new("RGB", (width, height), "#0054A6").save(content, image_format)
    return base64.b64encode(content.getvalue())


def size(picture_b64):
    with Image.open(io.BytesIO(base64.b64decode(picture_b64))) as img:
        return img.size


DOWNLOAD_LINK = (
    "/web/login?redirect=%2Fweb%2Fcontent%2Fevent.registration%2F{id}"
    "%2Fprofile_picture_original%3Fdownload%3Dtrue"
    "%26filename_field%3Dprofile_picture_original_filename"
)


class RegistrationCase(TransactionCase):
    """An event to register a participant to."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.event = cls.env["event.event"].create(
            {
                "name": "T3630 event",
                "date_begin": "2030-05-01 08:00:00",
                "date_end": "2030-05-10 18:00:00",
                "user_id": cls.env.user.id,
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "T3630 participant", "email": "t3630@example.com"}
        )

    def register(self, **vals):
        return (
            self.env["event.registration"]
            .with_context(bin_size=False)
            .create({"event_id": self.event.id, "partner_id": self.partner.id, **vals})
        )
