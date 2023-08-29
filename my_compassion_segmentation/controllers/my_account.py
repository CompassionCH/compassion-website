##############################################################################
#
#    Copyright (C) 2020 Compassion CH (http://www.compassion.ch)
#    @author: Théo Nikles <theo.nikles@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo.http import request, route

from odoo.addons.my_compassion.controllers.my_account import MyAccountController


class MyAccountControllerSurvey(MyAccountController):
    @route(["/my", "/my/home"], type="http", auth="user", website=True)
    def home(self, redirect=None, **post):
        partner = request.env.user.partner_id
        if not partner.has_segment:
            # Redirect to the segmentation survey
            survey = request.env.ref(
                "partner_segmentation.partner_segmentation_survey"
            ).sudo()
            return request.redirect(survey.get_start_url())
        else:
            return super().home(redirect, **post)
