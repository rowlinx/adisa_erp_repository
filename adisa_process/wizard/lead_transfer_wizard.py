# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, Warning, UserError


# TODO prendre en compte les devis déjà générés
class LeadTransferWizard(models.TransientModel):
    _name = 'lead.transfer.wizard'

    def _default_leads(self):
        return self.env['crm.lead'].browse(self._context.get('active_ids'))

    def action_confirm(self):
        for lead in self.lead_ids:
            lead.user_id = self.vendor.id

            for order in lead.order_ids:
                order.user_id = self.vendor.id

        return True

    lead_ids = fields.Many2many('crm.lead', string="BCF", required=True, default=_default_leads)
    vendor = fields.Many2one('res.users', string="Commercial", required=True)