##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import hashlib
import secrets
from datetime import timedelta

from odoo import api, fields, models

TOKEN_VALIDITY_DAYS = 30


class LoginToken(models.Model):
    """Single-use magic login links sent by email (T3569).

    Only a hash of the token is stored: the link in the email is the sole
    copy of the credential.
    """

    _name = "my2.login.token"
    _description = "MyCompassion magic login token"

    partner_id = fields.Many2one(
        "res.partner", required=True, readonly=True, ondelete="cascade", index=True
    )
    token_hash = fields.Char(required=True, readonly=True, index=True)
    expiration = fields.Datetime(required=True, readonly=True)
    used_date = fields.Datetime(readonly=True)

    _sql_constraints = [
        ("token_hash_uniq", "unique (token_hash)", "The token must be unique."),
    ]

    @staticmethod
    def _hash(token):
        return hashlib.sha256(token.encode()).hexdigest()

    @api.model
    def _issue(self, partner):
        token = secrets.token_urlsafe(32)
        self.sudo().create(
            {
                "partner_id": partner.id,
                "token_hash": self._hash(token),
                "expiration": fields.Datetime.now()
                + timedelta(days=TOKEN_VALIDITY_DAYS),
            }
        )
        return token

    @api.model
    def _find_valid(self, token):
        if not token:
            return self.browse()
        return self.sudo().search(
            [
                ("token_hash", "=", self._hash(token)),
                ("used_date", "=", False),
                ("expiration", ">", fields.Datetime.now()),
            ],
            limit=1,
        )

    def _consume(self):
        """Mark the token used. False when a concurrent request was first."""
        self.ensure_one()
        self.env.cr.execute(
            "UPDATE my2_login_token SET used_date = NOW() AT TIME ZONE 'UTC'"
            " WHERE id = %s AND used_date IS NULL RETURNING id",
            [self.id],
        )
        self.invalidate_recordset(["used_date"])
        return bool(self.env.cr.fetchone())

    @api.autovacuum
    def _gc_expired(self):
        self.sudo().search([("expiration", "<", fields.Datetime.now())]).unlink()
