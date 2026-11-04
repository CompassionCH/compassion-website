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

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import RegistrationCase, download_link, picture, size


@tagged("post_install", "-at_install")
class TestProfilePictureOriginal(RegistrationCase):
    """The uploaded profile picture is kept as it is for the staff (T3630)."""

    def test_picture_kept_as_uploaded(self):
        for image_format, extension in (("JPEG", "jpg"), ("PNG", "png")):
            with self.subTest(image_format=image_format):
                registration = self.register(
                    profile_picture=picture(4000, 3000, image_format)
                )

                self.assertEqual(size(registration.profile_picture), (4000, 3000))
                self.assertTrue(
                    registration._get_profile_picture_download_url().endswith(
                        download_link(registration, f"T3630 participant.{extension}")
                    )
                )
                registration.unlink()

    def test_picture_from_my_events_form_kept_as_uploaded(self):
        """The My events edit form writes the picture through a wizard."""
        registration = self.register()

        self.env["event.registration.form"].create(
            {
                "registration_id": registration.id,
                "profile_picture": picture(4000, 3000),
            }
        )

        self.assertEqual(size(registration.profile_picture), (4000, 3000))

    def test_unreadable_picture_names_the_formats(self):
        heic = base64.b64encode(b"\x00\x00\x00\x18ftypheic" + b"\x00" * 64)

        with self.assertRaisesRegex(ValidationError, "JPG or PNG"):
            self.register(profile_picture=heic)

    def test_huge_picture_refused(self):
        """Pillow refuses to open it at all (decompression bomb)."""
        content = io.BytesIO()
        Image.new("1", (14000, 13000)).save(content, "PNG")

        with self.assertRaisesRegex(ValidationError, "too large"):
            self.register(profile_picture=base64.b64encode(content.getvalue()))

    def test_duplicate_keeps_the_picture(self):
        registration = self.register(profile_picture=picture(4000, 3000))

        other = self.partner.copy({"name": "T3630 other participant"})

        duplicate = registration.copy({"partner_id": other.id})

        self.assertEqual(size(duplicate.profile_picture), (4000, 3000))

    def test_event_note_links_the_picture(self):
        registration = self.register(profile_picture=picture(4000, 3000))

        note = self.event.message_ids[:1]
        self.assertIn(f'data-oe-id="{registration.id}"', note.body)
        self.assertIn(download_link(registration, "T3630 participant.jpg"), note.body)

    def test_no_link_without_picture(self):
        registration = self.register()

        self.assertFalse(registration._get_profile_picture_download_url())
        self.assertNotIn("/web/content/", self.event.message_ids[:1].body)
