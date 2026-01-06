##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Nathan Felber <nfelber@compassion.ch>
#    @author: Elias Keller <elias@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

import json
import math
from collections import defaultdict
from datetime import datetime, timedelta

from werkzeug.exceptions import BadRequest, NotFound

import odoo
from odoo import _, fields, http
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal


class MyCompassionDonationsController(CustomerPortal):
    @http.route(
        '/my2/gifts/<model("product.template"):product>',
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def my2_render_donation_details_page(self, product, **kwargs):
        """
        Renders a donation details page for a specific donation (product).
        return: An HTTP response containing a rendered template with the donation
        details page.
        """
        sponsorships = request.env.user.partner_id.sponsorship_ids
        donation_limits = request.env["gift.threshold.settings"].sudo().search([])

        context = {
            "product": product,
            "sponsorships": sponsorships,
            "donation_limits": donation_limits,
        }

        return request.render(
            "my_compassion.my2_donation_details_page",
            context,
        )

    @http.route(
        "/my2/gifts/new",
        type="json",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def donation_new(self, **post):
        """
        Receives the donation submission and add it to the gift package of the user,
        then redirects to checkout (the gift package page).
        """
        # Fetch the product record from the database
        try:
            product_template_id = int(post.get("product_id"))
        except (ValueError, TypeError) as e:
            raise BadRequest() from e
        product_template = (
            request.env["product.template"].sudo().browse(product_template_id)
        )

        # Make sure the product is available
        if not product_template.activate_for_my_compassion:
            raise NotFound()

        # Get current cart content
        order = request.website.sale_get_order(force_create=True)

        # Add product to the cart
        order.write(
            {
                "order_line": [
                    (
                        0,
                        0,
                        self._extract_donation_order_line_fields(
                            product_template, post
                        ),
                    )
                ]
            }
        )

    @http.route(
        "/my2/gifts/edit",
        type="json",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def donation_edit(self, **post):
        """
        Edits a donation from the user's gift package.
        """
        # Fetch the order line record from the user's cart
        order = request.website.sale_get_order()
        order_line_id = post.get("order_line_id")
        order_line = order and order.order_line.filtered(
            lambda line: line.id == order_line_id
        )

        # Make sure the order line exists
        if not order_line:
            raise NotFound()

        product_template = order_line.product_template_id

        order_line.write(
            self._extract_donation_order_line_fields(product_template, post)
        )

    @http.route(
        "/my2/gifts/get-limits",
        type="json",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def donation_get_limits(self, product_id, sponsorship_id=None, **post):
        """
        Returns the donation limits for a product (and optionally a sponsorship)
        in the form:
        {
            "min_amount": int,               # If amount is limited
            "max_amount": int,               # If amount is limited
            "remaining_donations": int,      # If frequency is limited
        }
        """
        product = request.env["product.template"].search([("id", "=", product_id)])
        if not product:
            return BadRequest()
        if sponsorship_id is not None:
            try:
                sponsorship_id = int(sponsorship_id)
            except TypeError as e:
                raise BadRequest() from e

        limits = product.get_donation_limits(
            request.website.company_id, request.env.user.partner_id, sponsorship_id
        )
        return limits

    @http.route(
        "/my2/gift-package",
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def my2_render_gift_package_page(self, **kwargs):
        """
        Renders the gift package (cart) page.
        return: An HTTP response containing a rendered template with the gift
        package page.
        """
        # Get the current sales order and register it as last order
        # (usually done in a confirmation step that we don't have)
        order = request.website.sale_get_order()
        request.session["sale_last_order_id"] = order.id

        # Fetch gift thresholds
        limits = request.env["gift.threshold.settings"].sudo().search([])

        # Fetch acquirer
        acquirer = self._get_payment_acquirer()

        return request.render(
            "my_compassion.my2_gift_package_page",
            {
                "order": order,
                "limits": limits,
                "acquirer": acquirer,
            },
        )

    @http.route(
        "/my2/gift-package/render-edit-form",
        type="json",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def render_edit_form(self, **post):
        """
        Renders the edit form template for the given order line and returns it as HTML.
        return: A JSON response containing the rendered template html.
        """
        order = request.website.sale_get_order()

        order_line_id = post.get("order_line_id")
        order_line = order.order_line.filtered(lambda line: line.id == order_line_id)
        if not order_line:
            raise NotFound()

        limits = request.env["gift.threshold.settings"].sudo().search([])

        render_attrs = {
            "product": order_line.product_template_id,
            "submit_label": "Ok",
            "default_frequency": order_line.frequency,
            "default_suggested_amount": "custom",
            "default_custom_amount": order_line.price_total,
            "limits": limits,
            "date": fields.Date.today(),
            "currency_name": order.pricelist_id.currency_id.name,
        }

        if order_line.is_gift:
            render_attrs["sponsorships"] = order_line.order_partner_id.sponsorship_ids
            render_attrs["default_sponsorship_id"] = order_line.gift_recipient_id.id

        # Render and return the form
        html_content = request.env["ir.qweb"]._render(
            "my_compassion.DonationFormComponent", render_attrs
        )

        return {"html": html_content}

    @http.route(
        "/my2/gift-package/delete-item",
        type="json",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def remove_item(self, **post):
        """
        Deletes an item from the user's gift package
        and renders the new gift package content using the
        my_compassion.my2_gift_package_content template.
        return: A JSON response containing the rendered template html.
        """
        order = request.website.sale_get_order()

        order_line_id = post.get("order_line_id")
        order_line = order.order_line.filtered(lambda line: line.id == order_line_id)
        if order_line:
            # Delete the record
            order_line.unlink()
        else:
            raise NotFound()

        # Render and return the updated content
        html_content = request.env["ir.qweb"]._render(
            "my_compassion.my2_gift_package_content",
            {
                "order": order,
            },
        )

        return {
            "html": html_content,
            "is_order_empty": len(order.order_line) == 0,
        }

    @http.route(
        "/my2/gift-package/add",
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def my2_render_add_a_gift_page(self, **kwargs):
        """
        Renders the add a gift page to quickly add a gift to the gift package.
        return: An HTTP response containing a rendered template with the add a
        gift page.
        """
        # Exclude fund donation that are already in the user's gift package
        order = request.website.sale_get_order(force_create=True)
        product_template_ids_in_cart = order.order_line.product_id.product_tmpl_id.ids
        products = request.env["product.template"].search(
            [
                "&",
                ("activate_for_my_compassion", "=", True),
                "|",
                ("my_compassion_donation_type", "=", "gift"),
                ("id", "not in", product_template_ids_in_cart),
            ]
        )

        sponsorships = request.env.user.partner_id.sponsorship_ids
        limits = request.env["gift.threshold.settings"].sudo().search([])

        return request.render(
            "my_compassion.my2_add_a_gift_page",
            {
                "products": products,
                "sponsorships": sponsorships,
                "limits": limits,
                "currency_name": order.pricelist_id.currency_id.name,
            },
        )

    @http.route(
        "/my2/gifts/thankyou",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def my2_gifts_thank_you_page(self, **kwargs):
        sale_order_id = request.session.get("sale_last_order_id")
        if sale_order_id:
            sale_order = request.env["sale.order"].sudo().browse(sale_order_id)
            return request.render(
                "my_compassion.my2_gifts_thank_you_page",
                {"sale_order": sale_order},
            )
        return request.redirect("/my2/dashboard")

    @staticmethod
    def _extract_donation_order_line_fields(product_template, post):
        # Compute quantity
        price = 0
        amount = post.get("suggested_amount")
        if amount == "custom":
            try:
                price = float(post.get("custom_amount"))
            except (ValueError, TypeError) as e:
                raise BadRequest() from e
            # Make sure price is strictly positive
            if price <= 0:
                raise BadRequest()
        else:
            quantities = {
                "low": product_template.my_compassion_donation_quantity_low,
                "medium": product_template.my_compassion_donation_quantity_medium,
                "high": product_template.my_compassion_donation_quantity_high,
            }
            quantity = quantities.get(amount)
            if not quantity:
                raise BadRequest()
            price = quantity * product_template.list_price

        # Get frequency
        frequency = post.get("frequency")

        product = product_template.product_variant_id
        order_line_fields = {
            "product_id": product.id,
            "price_unit": price,
            "frequency": frequency,
        }
        if product_template.my_compassion_donation_type == "gift":
            order_line_fields["is_gift"] = True
            order_line_fields["gift_recipient_id"] = post.get("recipient")

        return order_line_fields

    def _get_paid_invoices_filter(self, partner):
        paid_invoices_filter = [
            ("partner_id", "=", partner.id),
            ("payment_state", "=", "paid"),
            ("move_type", "=", "out_invoice"),
            ("amount_total", "!=", 0),
        ]
        return paid_invoices_filter

    def _get_paid_invoices_subset(self, partner, offset, amount):
        paid_invoices_subset = (
            request.env["account.move"]
            .sudo()
            .search(
                self._get_paid_invoices_filter(partner),
                offset=offset,
                limit=amount,
            )
        )
        return paid_invoices_subset

    def _get_paid_invoices_amount(self, partner):
        number_of_paid_invoices = (
            request.env["account.move"]
            .sudo()
            .search_count(self._get_paid_invoices_filter(partner))
        )
        return number_of_paid_invoices

    # -------------------------------------------------------------------------
    # Methods and routes for MyCompassion2.0 Donations Page
    # -------------------------------------------------------------------------

    @http.route(
        "/my2/donations",
        type="http",
        auth="user",
        website=True,
    )
    def my_donations(self, invoice_page=1, invoice_per_page=12, **kw):
        partner = request.env.user.partner_id

        # Active sponsorships
        active_sponsorships = partner.get_portal_sponsorships(["active", "mandate"])

        # Group sponsorships by their backend Contract Group
        sponsorship_groups = active_sponsorships.mapped("group_id")

        # Put all payment methods into an array
        all_groups = partner.get_payment_modes()
        payment_methods = [group.get_payment_method_info() for group in all_groups]

        # Due invoices
        date_filter_up_bound = datetime.today() + timedelta(days=30)
        due_invoices = (
            request.env["account.move"]
            .sudo()
            .search(
                [
                    ("partner_id", "=", partner.id),
                    ("payment_state", "=", "not_paid"),
                    ("invoice_category", "=", "sponsorship"),
                    ("move_type", "=", "out_invoice"),
                    ("state", "=", "posted"),
                    ("amount_total", "!=", 0),
                    ("invoice_date", "<", fields.Date.to_string(date_filter_up_bound)),
                ]
            )
        )

        # Total cost calculation
        tot_cost_per_frequency = defaultdict(lambda: defaultdict(float))

        for sponsorship in active_sponsorships:
            currency = sponsorship.pricelist_id.currency_id.name
            # Ensure group exists
            if sponsorship.group_id:
                tot_cost_per_frequency[sponsorship.group_id.month_interval][
                    currency
                ] += sponsorship.total_amount

        paid_invoices_data = self._get_paginated_paid_invoices(
            partner, invoice_page, invoice_per_page
        )

        values = self._prepare_portal_layout_values()
        values.update(
            {
                "active_sponsorships": active_sponsorships,
                "sponsorship_groups": sponsorship_groups,
                "payment_methods": payment_methods,
                "payment_methods_json": json.dumps(payment_methods),
                "tot_cost_per_frequency": tot_cost_per_frequency,
                "due_invoices": due_invoices,
                "paid_invoices_subset": paid_invoices_data["paid_invoices_subset"],
                "current_page": paid_invoices_data["current_page"],
                "total_pages": paid_invoices_data["total_pages"],
            }
        )
        return request.render("my_compassion.my2_my_donations_page", values)

    @http.route(
        "/my2/donations/history",
        type="json",
        auth="user",
        methods=["POST"],
        website=True,
    )
    def my_donations_history(self, invoice_page=1, invoice_per_page=12, **kw):
        partner = request.env.user.partner_id

        history_data = self._get_paginated_paid_invoices(
            partner, invoice_page, invoice_per_page
        )

        html = request.env["ir.qweb"]._render(
            "my_compassion.my2_donations_history_content",
            values=history_data,
        )

        return {"html": html}

    @http.route(
        "/my2/donations/get_payment_methods_sponsor",
        type="json",
        auth="user",
        website=True,
    )
    def get_payment_methods_sponsor(self, **kwargs):
        """
        Returns a list of payment methods (saved tokens and acquirers) for the current
        user.
        """
        partner = request.env.user.partner_id
        groups = partner.get_payment_modes()
        payment_methods = []

        for group in groups:
            info = group.get_payment_method_info()
            if not info:
                continue
            method = dict(info)
            method["group_id"] = group.id

            payment_methods.append(method)

        return payment_methods

    @http.route(
        "/my2/donation/change_method_contract", type="json", auth="user", website=True
    )
    def change_payment_method_contract(self, contract_id, group_id, **kwargs):
        """
        Changes the payment method for a specific contract.

        :param contract_id: ID of the recurring.contract to update.
        :param group_id: ID of an existing group to merge into
        """
        partner = request.env.user.partner_id
        if not contract_id or not group_id:
            raise BadRequest()
        # Verify that the contract belongs to the user
        contract = (
            request.env["recurring.contract"]
            .sudo()
            .search([("id", "=", int(contract_id)), ("partner_id", "=", partner.id)])
        )
        if not contract:
            raise NotFound()

        success = contract.change_contract_group(int(group_id))
        if success:
            # Render the updated list
            values = self._prepare_sponsorship_values(partner)
            html = request.env["ir.qweb"]._render(
                "my_compassion.my2_sponsorships_section", values
            )
            return {
                "success": True,
                "html": html,
                "payment_methods": values["payment_methods"],
            }

        return {"success": False, "error": _("Operation failed")}

    @http.route(
        "/my2/donation/change_method_group", type="json", auth="user", website=True
    )
    def change_payment_method_group(
            self, group_id, new_group_id=None, new_bvr_ref=None, **kwargs
    ):
        """
        Endpoint to update payment method for a sponsorship group.
        Accepts new_group_id (to merge) or new_bvr_ref (to update ref).
        """
        partner = request.env.user.partner_id

        if not group_id:
            raise BadRequest(_("Group ID is required."))

        # Security Check: Search ensures the group belongs to the logged-in user
        group = (
            request.env["recurring.contract.group"]
            .sudo()
            .search(
                [("id", "=", int(group_id)), ("partner_id", "=", partner.id)], limit=1
            )
        )

        if not group:
            raise NotFound(_("Payment group not found or access denied."))

        # Call the model method to perform the logic
        success = group.change_payment_method(
            new_group_id=new_group_id, new_bvr_ref=new_bvr_ref
        )

        if success:
            values = self._prepare_sponsorship_values(partner)
            html = request.env["ir.qweb"]._render(
                "my_compassion.my2_sponsorships_section", values
            )
            return {
                "success": True,
                "html": html,
                "payment_methods": values["payment_methods"],
            }

        return {"success": False, "error": _("Operation failed")}

    @http.route(
        "/my2/donation/add_payment_method_group", type="json", auth="user", website=True
    )
    def add_payment_method_group(self, recurring_unit="month", method_type="bvr", advance_billing_months=1, **kwargs):
        """
        Creates a new Contract Group with manual BVR/Permanent Order details.
        """
        partner = request.env.user.partner_id

        # 1. Find Payment Mode
        payment_mode = self._find_manual_payment_mode(method_type)
        if not payment_mode:
            return {
                "success": False,
                "error": _('Configuration Error: Payment mode for "%s" not found.') % method_type,
            }

        # 2. Create the Group
        try:
            new_group = self._create_contract_group(
                partner, payment_mode, recurring_unit, advance_billing_months
            )

            # Specific BVR Logic
            new_bvr_ref = new_group.compute_partner_bvr_ref(partner)
            if new_bvr_ref:
                new_group.bvr_reference = new_bvr_ref

            # 3. Return HTML
            values = self._prepare_sponsorship_values(partner)
            html = request.env["ir.qweb"]._render("my_compassion.my2_sponsorships_section", values)

            return {
                "success": True,
                "html": html,
                "group_id": new_group.id,
                "payment_methods": values["payment_methods"],
            }

        except odoo.exceptions.ValidationError as e:
            return {"success": False, "error": str(e)}
        except Exception:
            return {"success": False, "error": _("An unexpected error occurred.")}



    @http.route('/my2/donation/add_payment_method_online', type='json', auth='user', website=True)
    def add_payment_method_online(self, recurring_unit='month', recurring_value=1, **kwargs):
        """
        Initiates a 'validation' transaction to tokenize a card/method without an immediate charge.
        Returns data for rendering the PostFinance Iframe with available methods.
        """
        partner = request.env.user.partner_id
        acquirer = self._get_payment_acquirer()

        if not acquirer.exists():
            return {'success': False, 'error': 'No payment provider found'}

        # Prepare Transaction
        return_url = '/my2/donations?unit={}&val={}'.format(recurring_unit, recurring_value)
        reference = 'ADD-METHOD-{}-{}'.format(partner.id, fields.Datetime.now().strftime('%Y%m%d%H%M%S'))

        transaction_values = {
            'acquirer_id': acquirer.id,
            'reference': reference,
            'amount': 0.0,
            'currency_id': request.website.currency_id.id,
            'partner_id': partner.id,
            'partner_country_id': partner.country_id.id,
            'type': 'validation',
            'return_url': return_url,
        }

        tx = request.env['payment.transaction'].sudo().create(transaction_values)
        request.session['add_method_tx_id'] = tx.id

        # 3. Get Integration Data (Iframe Only)
        # This calls the method overridden in 'my_compassion_switzerland'
        result_data = self._prepare_postfinance_iframe_redirect(acquirer, tx, return_url)

        if result_data and isinstance(result_data, dict) and result_data.get('type') == 'iframe':
            return {
                'success': True,
                'iframe_url': result_data['url'],
                'pf_methods': result_data.get('pf_methods', [])
            }

        # 4. Error if Iframe data is missing (No longer supporting HTML fallback)
        return {'success': False, 'error': 'Payment interface could not be loaded.'}

    @http.route('/my2/donation/set_selected_payment_method', type='json', auth='user', website=True)
    def set_selected_payment_method(self, method_name):
        """
        Called by JS when the user selects an online method (e.g. 'Credit Card', 'Visa').
        Stores it in the session so we can find the correct Payment Mode later.
        """
        request.session['add_method_name'] = method_name
        return True

    # -------------------------------------------------------------------------
    # PRIVATE HELPERS (Rendering Data Preparation)
    # -------------------------------------------------------------------------

    def _prepare_sponsorship_values(self, partner):
        """
        Helper to fetch all data required for the sponsorship list view.
        Returns a dict of values for QWeb rendering.
        """
        # 1. Fetch Active Sponsorships
        active_sponsorships = partner.get_portal_sponsorships(["active", "mandate"])

        # 2. Fetch Groups
        sponsorship_groups = active_sponsorships.mapped("group_id")

        # 3. Calculate Totals
        tot_cost_per_frequency = defaultdict(lambda: defaultdict(float))
        for sponsorship in active_sponsorships:
            currency = sponsorship.pricelist_id.currency_id.name
            if sponsorship.group_id:
                tot_cost_per_frequency[sponsorship.group_id.month_interval][
                    currency
                ] += sponsorship.total_amount

        # 4. Fetch Available Methods (for modals)
        all_groups = partner.get_payment_modes()
        payment_methods = [group.get_payment_method_info() for group in all_groups]

        return {
            "active_sponsorships": active_sponsorships,
            "sponsorship_groups": sponsorship_groups,
            "tot_cost_per_frequency": tot_cost_per_frequency,
            "payment_methods": payment_methods,
            "payment_methods_json": json.dumps(payment_methods),
        }

    def _get_paginated_paid_invoices(
            self, partner, invoice_page=1, invoice_per_page=12
    ):
        """
        Fetches a paginated subset of paid invoices for a partner and calculates
        pagination details.
        """
        offset = (int(invoice_page) - 1) * invoice_per_page

        subset = self._get_paid_invoices_subset(partner, offset, invoice_per_page)

        total_amount = self._get_paid_invoices_amount(partner)

        total_pages = (
            math.ceil(total_amount / invoice_per_page) if invoice_per_page > 0 else 0
        )

        return {
            "paid_invoices_subset": subset,
            "current_page": int(invoice_page),
            "total_pages": total_pages,
        }

    def _create_contract_group(self, partner, payment_mode, unit, value, token=None):
        """
        Centralized method to create a recurring contract group.
        Used by both Manual (BVR) and Online (Credit Card) flows.
        """
        vals = {
            "partner_id": partner.id,
            "payment_mode_id": payment_mode.id,
            "recurring_unit": unit,
            "recurring_value": int(value),
            "active": True,
        }
        if token:
            vals['payment_token_id'] = token.id

        return request.env["recurring.contract.group"].sudo().create(vals)

    def _find_manual_payment_mode(self, method_key):
        """
        Finds a payment mode based on the frontend key (bvr/permanent).
        Handles case-insensitive search and archiving.
        """
        # Map frontend keys to DB names
        search_map = {
            "permanent_order": "Permanent Order",
            "bvr": "BVR",
        }
        term = search_map.get(method_key)
        if not term:
            return None

        # Search with active_test=False to find modes even if archived/hidden
        domain = [("name", "=", term)]
        mode = request.env["account.payment.mode"].sudo().with_context(active_test=False).search(domain, limit=1)

        # Fallback: Fuzzy search
        if not mode:
            mode = request.env["account.payment.mode"].sudo().with_context(active_test=False).search(
                [("name", "ilike", term)], limit=1
            )
        return mode

    def _find_online_payment_mode(self, acquirer, method_name_from_api=None):
        """
        Smart search for online payment modes (Twint, Visa, etc).
        Strategy: Name Match -> Journal Match -> Generic Fallback.
        """
        company_id = request.website.company_id.id
        base_domain = [
            ('company_id', '=', company_id),
            ('payment_type', '=', 'inbound'),
            ('state', '=', 'active')
        ]

        payment_mode = False

        # 1. Search by Name (e.g. "Twint")
        if method_name_from_api:
            payment_mode = request.env['account.payment.mode'].sudo().search(
                base_domain + [('name', 'ilike', method_name_from_api)], limit=1
            )

        # 2. Fallback to Acquirer's Journal
        if not payment_mode and acquirer.journal_id:
            payment_mode = request.env['account.payment.mode'].sudo().search(
                base_domain + [('fixed_journal_id', '=', acquirer.journal_id.id)], limit=1
            )

        # 3. Generic Fallback
        if not payment_mode:
            payment_mode = request.env['account.payment.mode'].sudo().search(base_domain, limit=1)

        return payment_mode

    @staticmethod
    def _get_payment_acquirer():
        return (
            http.request.env["payment.acquirer"]
            .sudo()
            .search([("provider", "=", "postfinance")], limit=1)
        )
