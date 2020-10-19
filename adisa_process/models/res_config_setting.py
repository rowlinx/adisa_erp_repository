# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    condition_of_sale = fields.Char(string='Conditions générales de vente',
                                    config_parameter='adisa_process.condition_of_sale')

    periodicity = fields.Selection([('day', 'Jour(s)'),
                                    ('week', 'Semaine(s)'),
                                    ('month', 'Mois'),
                                    ('annual', 'Année(s)')], string="Période", default='day',
                                   config_parameter='adisa_process.periodicity')
    interval = fields.Integer(string="Temps", default=5, config_parameter='adisa_process.interval')

    # @api.model
    # def get_values(self):
    #     res = super(ResConfigSettings, self).get_values()
    #     ICPSudo = self.env['ir.config_parameter'].sudo()
    #     condition_of_sale = ICPSudo.get_param('adisa_process.condition_of_sale')
    #     periodicity = ICPSudo.get_param('adisa_process.periodicity')
    #     interval = ICPSudo.get_param('adisa_process.interval')
    #
    #     res.update(
    #         condition_of_sale=condition_of_sale,
    #         periodicity=periodicity,
    #         interval=interval,
    #     )
    #
    #     return res

    # @api.model
    # def set_values(self):
    #     res = super(ResConfigSettings, self).set_values()
    #     self.env['ir.config_parameter'].set_param('adisa_process.condition_of_sale', self.condition_of_sale)
    #     self.env['ir.config_parameter'].set_param('adisa_process.periodicity', self.periodicity)
    #     self.env['ir.config_parameter'].set_param('adisa_process.interval', self.interval)
    #     return res
