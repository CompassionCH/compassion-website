##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import base64

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import DOWNLOAD_LINK, RegistrationCase, picture, size


@tagged("post_install", "-at_install")
class TestProfilePictureOriginal(RegistrationCase):
    """The uploaded profile picture is kept as it is for the staff (T3630)."""

    def test_original_kept_beside_the_capped_picture(self):
        for image_format, extension in (("JPEG", "jpg"), ("PNG", "png")):
            with self.subTest(image_format=image_format):
                registration = self.register(
                    profile_picture=picture(4000, 3000, image_format)
                )

                self.assertEqual(size(registration.profile_picture), (1920, 1440))
                self.assertEqual(
                    size(registration.profile_picture_original), (4000, 3000)
                )
                self.assertEqual(
                    registration.profile_picture_original_filename,
                    f"T3630 participant.{extension}",
                )
                registration.unlink()

    def test_unreadable_picture_names_the_formats(self):
        heic = base64.b64encode(b"\x00\x00\x00\x18ftypheic" + b"\x00" * 64)

        with self.assertRaisesRegex(ValidationError, "JPG or PNG"):
            self.register(profile_picture=heic)

    def test_new_picture_replaces_the_original(self):
        registration = self.register(profile_picture=picture(4000, 3000))

        registration.profile_picture = picture(1200, 2000)

        self.assertEqual(size(registration.profile_picture_original), (1200, 2000))

    def test_event_note_links_the_original(self):
        registration = self.register(profile_picture=picture(4000, 3000))

        note = self.event.message_ids[:1]
        self.assertIn(f'data-oe-id="{registration.id}"', note.body)
        self.assertIn(DOWNLOAD_LINK.format(id=registration.id), note.body)

    def test_no_link_without_picture(self):
        registration = self.register()

        self.assertFalse(registration._get_profile_picture_download_url())
        self.assertNotIn("profile_picture_original", self.event.message_ids[:1].body)
