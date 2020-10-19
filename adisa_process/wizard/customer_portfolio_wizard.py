# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, Warning, UserError


class CustomerPortfolioWizard(models.TransientModel):
    _name = 'customer.portfolio.wizard'

    def _default_customers(self):
        return self.env['res.partner'].browse(self._context.get('active_ids'))

    def action_confirm(self):
        for customer in self.customer_ids:
            customer.user_id = self.vendor.id

        return True

    customer_ids = fields.Many2many('res.partner', string="BCF", required=True, default=_default_customers,
                                    domain=[('company_type', '=', 'company'),
                                            ('society_nature', 'in', ('prospect', 'customer', 'prescript'))])
    vendor = fields.Many2one('res.users', string="Commercial", required=True)
