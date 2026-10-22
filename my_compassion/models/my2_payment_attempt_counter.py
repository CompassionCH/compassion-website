##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from datetime import timedelta

from odoo import api, fields, models
from odoo.tools import SQL


class PaymentAttemptCounter(models.Model):
    """The payments visitors start on a MyCompassion website, per client IP,
    over a window of website.my2_payment_attempts_window minutes, all carts
    and sessions together: card testers try stolen cards one after the
    other, with a new session and cart whenever one is limited.

    One row per website and IP, written in place by an upsert. Two requests
    of the same IP therefore write the same row: the second waits for the
    first and, under Odoo's REPEATABLE READ isolation, fails with a
    serialization error once the first commits; Odoo retries it, with a
    snapshot that counts the first attempt. A lock alone would not do: the
    waiting request would still count in its older snapshot.
    """

    _name = "my2.payment.attempt.counter"
    _description = "MyCompassion visitor payment attempts per IP"
    _log_access = False

    website_id = fields.Many2one(
        "website", required=True, readonly=True, ondelete="cascade"
    )
    ip_address = fields.Char("IP Address", required=True, readonly=True)
    window_start = fields.Datetime(required=True, readonly=True)
    attempts = fields.Integer(required=True, readonly=True)

    _sql_constraints = [
        (
            "website_ip_unique",
            "UNIQUE(website_id, ip_address)",
            "One counter per website and IP address.",
        )
    ]

    @api.model
    def _my2_count_attempt(self, order, ip_address):
        """Count a payment of order, a MyCompassion order, started from
        ip_address. Whether it stays within the limit of the order's website
        (the caller refuses it otherwise, which rolls the count back)."""
        website = order.website_id
        limit = website.my2_max_payment_attempts_per_ip
        if limit <= 0:
            return True
        now = fields.Datetime.now()
        since = now - timedelta(minutes=website.my2_payment_attempts_window)
        self.env.cr.execute(
            SQL(
                """
                INSERT INTO my2_payment_attempt_counter AS counter
                    (website_id, ip_address, window_start, attempts)
                VALUES (%(website)s, %(ip)s, %(now)s, 1)
                ON CONFLICT (website_id, ip_address) DO UPDATE SET
                    attempts = CASE WHEN counter.window_start < %(since)s
                        THEN 1 ELSE counter.attempts + 1 END,
                    window_start = CASE WHEN counter.window_start < %(since)s
                        THEN %(now)s ELSE counter.window_start END
                RETURNING attempts
                """,
                website=website.id,
                ip=ip_address or "",
                now=now,
                since=since,
            )
        )
        attempts = self.env.cr.fetchone()[0]
        self.invalidate_model()
        return attempts <= limit

    @api.autovacuum
    def _gc_my2_expired_counters(self):
        """The counters whose window is over: the next attempt of their IP
        starts a new one."""
        self.flush_model(["website_id", "window_start"])
        self.env["website"].flush_model(["my2_payment_attempts_window"])
        self.env.cr.execute(
            SQL(
                """
                DELETE FROM my2_payment_attempt_counter counter
                USING website
                WHERE website.id = counter.website_id
                    AND counter.window_start < %s
                        - make_interval(mins => website.my2_payment_attempts_window)
                """,
                fields.Datetime.now(),
            )
        )
        self.invalidate_model()
