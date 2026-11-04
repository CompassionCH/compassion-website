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

from odoo.tests import HttpCase, tagged

from .common import RegistrationCase

GPS_IFD = 0x8825
CAMERA_MAKE = 0x010F


@tagged("post_install", "-at_install")
class TestPublicPhoto(HttpCase, RegistrationCase):
    """The public gets a bounded copy of the picture without its metadata,
    not the file stored for the staff (T3630)."""

    def test_public_photo_bounded_without_metadata(self):
        exif = Image.Exif()
        exif[CAMERA_MAKE] = "T3630 phone"
        exif.get_ifd(GPS_IFD).update({1: "N", 2: (46.0, 31.0, 12.0)})
        content = io.BytesIO()
        Image.new("RGB", (4000, 3000), "#0054A6").save(content, "JPEG", exif=exif)
        registration = self.register(
            profile_picture=base64.b64encode(content.getvalue())
        )
        registration.is_published = True
        with Image.open(
            io.BytesIO(base64.b64decode(registration.profile_picture))
        ) as img:
            self.assertEqual(img.getexif()[CAMERA_MAKE], "T3630 phone")

        response = self.url_open(f"/event/registration/{registration.id}/photo")

        self.assertEqual(response.status_code, 200)
        with Image.open(io.BytesIO(response.content)) as img:
            self.assertEqual(img.size, (1920, 1440))
            self.assertFalse(img.getexif())

    def test_requested_size_still_served(self):
        content = io.BytesIO()
        Image.new("RGB", (4000, 3000), "#0054A6").save(content, "JPEG")
        registration = self.register(
            profile_picture=base64.b64encode(content.getvalue())
        )
        registration.is_published = True

        response = self.url_open(f"/event/registration/{registration.id}/photo/300x300")

        with Image.open(io.BytesIO(response.content)) as img:
            self.assertEqual(img.size, (300, 225))
