# -*- coding: utf-8 -*-
import sys
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, Warning, UserError

READONLY_STATES = {
    'purchase': [('readonly', True)],
    'done': [('readonly', True)],
    'cancel': [('readonly', True)],
}


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    line_id = fields.Many2one('product.purchase.composition')
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True, states=READONLY_STATES,
                                 change_default=True, tracking=True,
                                 domain="[('contact_type', '=', 'suppliers')]",
                                 help="You can find a vendor by its Name, TIN, Email or Internal Reference.")


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def order_verification_periodicity(self):
        sys.stdout.write("CRON EN COURS")

        orders = self.env['sale.order'].search([('id', '!=', False)])

        for order in orders:
            order.update({'name': 'Mon cron marche !!!'})

    def _get_conditions(self):
        ICPsudo = self.env['ir.config_parameter'].sudo()
        condition = ICPsudo.get_param('adisa_process.condition_of_sale')
        return condition

        return self

    def submit(self):
        self.write({'state': 'validation'})

    def validation(self):
        self.write({'state': 'draft'})

    def reject(self):
        self.write({'state': 'basic'})

    state = fields.Selection([
        ('basic', 'Brouillon'),
        ('validation', 'Validation'),
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='basic')
    condition_sale = fields.Char(string="Conditions générales de vente", default=_get_conditions)
    partner_id = fields.Many2one(
        'res.partner', string='Customer', readonly=True,
        states={'basic': [('readonly', False)], 'validation': [('readonly', False)], 'draft': [('readonly', False)],
                'sent': [('readonly', False)]},
        required=True, change_default=True, index=True, tracking=1,
        domain="[('contact_type', 'in', ['prospect', 'customer'])]", )
    partner_invoice_id = fields.Many2one(
        'res.partner', string='Invoice Address',
        readonly=True, required=True,
        states={'basic': [('readonly', False)], 'validation': [('readonly', False)], 'draft': [('readonly', False)],
                'sent': [('readonly', False)], 'sale': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", )
    partner_shipping_id = fields.Many2one(
        'res.partner', string='Delivery Address', readonly=True, required=True,
        states={'basic': [('readonly', False)], 'validation': [('readonly', False)], 'draft': [('readonly', False)],
                'sent': [('readonly', False)], 'sale': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", )
    pricelist_id = fields.Many2one(
        'product.pricelist', string='Pricelist', check_company=True,  # Unrequired company
        required=True, readonly=True,
        states={'basic': [('readonly', False)], 'validation': [('readonly', False)], 'draft': [('readonly', False)],
                'sent': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="If you change the pricelist, only newly added lines will be affected.")


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    duration = fields.Integer(string="Durée", default=1)
    categ_id = fields.Many2one('product.category', string="Catégorie", related="product_id.categ_id")

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'duration')
    def _compute_amount(self):
        super(SaleOrderLine, self)._compute_amount()
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            quantity = line.product_uom_qty * line.duration
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, quantity,
                                            product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    @api.onchange('product_id')
    def _get_price(self):
        if self.product_id and self.product_id.lst_price:
            self.price_unit = self.product_id.lst_price
        else:
            self.price_unit = 0

    def write(self, vals):
        if self.discount and not self.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
            if self.discount > 10 or self.discount > self.product_id.margin_rate:
                raise ValidationError(
                    u"Vous ne pouvez faire une réduction supérieure à la marge produit ou à 10%"
                )

        if self.product_id and self.product_id.lst_price and 'price_unit' in vals.keys() and not self.env.user.has_group(
                'sales_team.group_sale_salesman_all_leads'):
            diff = (self.product_id.lst_price - self.price_unit) * 100 / self.product_id.lst_price
            print(diff)
            if diff < -10 or diff > 10:
                raise ValidationError(
                    u"Vous ne pouvez modifier le prix unitaire de -10% à 10%"
                )

        super(SaleOrderLine, self).write(vals)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.onchange('lst_price', 'standard_price')
    def _get_margin(self):
        if self.lst_price:
            self.margin_rate = (self.lst_price - self.standard_price) * 100 / self.lst_price
        else:
            self.margin_rate = 0

    margin_ids = fields.One2many('product.purchase.composition', 'product_id', string="Composition produit")
    margin_rate = fields.Float(string="Marge %", compute=_get_margin)
    duration = fields.Integer(string="Durée", default=1)

    @api.model
    def create(self, vals):
        product = super(ProductTemplate, self).create(vals)
        if product.margin_ids and vals['standard_price'] == 0:
            product.standard_price = sum([margin_id.cost for margin_id in product.margin_ids])

        return product

    def write(self, vals):
        product = super(ProductTemplate, self).write(vals)
        if self.margin_ids and 'standard_price' not in vals.keys():
            self.standard_price = sum([margin_id.cost for margin_id in self.margin_ids])

        return product


class MarginProduct(models.Model):
    _name = 'product.purchase.composition'
    _description = 'adisa_process.adisa_process'

    # def action_confirm(self):
    #     for line in self:
    #         order = self.env['purchase.order'].create({
    #             'line_id': line.id,
    #             'partner_id': line.partner_id.id,
    #             'state': 'draft',
    #             'date_start': line.date_start,
    #             'date': line.date,
    #         })
    #         order_line = self.env['purchase.order.line'].create({
    #             'product_id': line.product_id.id,
    #             'name': line.description,
    #             'date_planned': datetime.now(),
    #             'product_qty': line.product_uom_qty,
    #             'duration': line.duration,
    #             'number': line.number,
    #             'product_uom': 1,
    #             'price_unit': line.price_unit,
    #             'taxes_id': line.tax_id.mapped('id'),
    #             'order_id': order.id,
    #             'discount': line.discount,
    #             # 'honorary': line.honorary
    #         })
    #         line.update({'purchase_id': order.id})
    #
    #         if state == 'draft':
    #             order.send_mail('email_purchase_price')
    #         else:
    #             order.send_mail('email_purchase_bcf')
    #
    #         return order_line

    partner_id = fields.Many2one('res.partner', string="Fournisseur")
    product_id = fields.Many2one('product.template', string="Produit", required=True, ondelete='cascade')
    cost = fields.Float(string="Coût")
    description = fields.Text(string="Description")


class SaleSubscription(models.Model):
    _inherit = "sale.subscription"

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, auto_join=True,
                                 domain="[('contact_type', 'in', ['prospect', 'customer'])]")

    def _prepare_renewal_order_values(self):
        res = dict()
        for subscription in self:
            order_lines = []
            fpos_id = self.env['account.fiscal.position'].with_context(
                force_company=subscription.company_id.id).get_fiscal_position(subscription.partner_id.id)
            for line in subscription.recurring_invoice_line_ids:
                order_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.product_id.product_tmpl_id.name,
                    'subscription_id': subscription.id,
                    'product_uom': line.uom_id.id,
                    'product_uom_qty': line.quantity,
                    'duration': line.duration,
                    'price_unit': line.price_unit,
                    'discount': line.discount,
                }))
            addr = subscription.partner_id.address_get(['delivery', 'invoice'])
            sale_order = subscription.env['sale.order'].search(
                [('order_line.subscription_id', '=', subscription.id)],
                order="id desc", limit=1)
            res[subscription.id] = {
                'pricelist_id': subscription.pricelist_id.id,
                'partner_id': subscription.partner_id.id,
                'partner_invoice_id': addr['invoice'],
                'partner_shipping_id': addr['delivery'],
                'currency_id': subscription.pricelist_id.currency_id.id,
                'order_line': order_lines,
                'analytic_account_id': subscription.analytic_account_id.id,
                'subscription_management': 'renew',
                'origin': subscription.code,
                'note': subscription.description,
                'fiscal_position_id': fpos_id,
                'user_id': subscription.user_id.id,
                'payment_term_id': sale_order.payment_term_id.id if sale_order else subscription.partner_id.property_payment_term_id.id,
                'company_id': subscription.company_id.id,
            }
        return res


class SaleSubscriptionLine(models.Model):
    _inherit = "sale.subscription.line"

    duration = fields.Integer(string="Durée", default=1)

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            self.duration = self.product_id.duration

    @api.depends('price_unit', 'quantity', 'duration', 'discount', 'analytic_account_id.pricelist_id')
    def _compute_price_subtotal(self):
        AccountTax = self.env['account.tax']
        for line in self:
            price = AccountTax._fix_tax_included_price(line.price_unit, line.product_id.sudo().taxes_id, AccountTax)
            line.price_subtotal = line.quantity * line.duration * price * (100.0 - line.discount) / 100.0
            if line.analytic_account_id.pricelist_id.sudo().currency_id:
                line.price_subtotal = line.analytic_account_id.pricelist_id.sudo().currency_id.round(
                    line.price_subtotal)

    @api.onchange('product_id', 'quantity', 'duration')
    def onchange_product_quantity(self):
        subscription = self.analytic_account_id
        company_id = subscription.company_id.id
        pricelist_id = subscription.pricelist_id.id
        quantity = self.quantity * self.duration
        context = dict(self.env.context, company_id=company_id, force_company=company_id, pricelist=pricelist_id,
                       quantity=quantity)
        if not self.product_id:
            self.price_unit = 0.0
        else:
            partner = subscription.partner_id.with_context(context)
            if partner.lang:
                context.update({'lang': partner.lang})

            product = self.product_id.with_context(context)
            if subscription.pricelist_id and subscription.pricelist_id.discount_policy == "without_discount":
                if subscription.pricelist_id.currency_id != self.product_id.currency_id:
                    self.price_unit = self.product_id.currency_id._convert(
                        self.product_id.lst_price,
                        subscription.pricelist_id.currency_id,
                        self.product_id.product_tmpl_id._get_current_company(pricelist=subscription.pricelist_id),
                        fields.Date.today()
                    )
                else:
                    self.price_unit = product.lst_price
                self.discount = (self.price_unit - product.price) / self.price_unit * 100
            else:
                self.price_unit = product.price

            if not self.uom_id or product.uom_id.category_id.id != self.uom_id.category_id.id:
                self.uom_id = product.uom_id.id
            if self.uom_id.id != product.uom_id.id:
                self.price_unit = product.uom_id._compute_price(self.price_unit, self.uom_id)

    def _amount_line_tax(self):
        self.ensure_one()
        val = 0.0
        product = self.product_id
        product_tmp = product.sudo().product_tmpl_id
        quantity = self.quantity * self.duration
        for tax in product_tmp.taxes_id.filtered(lambda t: t.company_id == self.analytic_account_id.company_id):
            fpos_obj = self.env['account.fiscal.position']
            partner = self.analytic_account_id.partner_id
            fpos_id = fpos_obj.with_context(force_company=self.analytic_account_id.company_id.id).get_fiscal_position(
                partner.id)
            fpos = fpos_obj.browse(fpos_id)
            if fpos:
                tax = fpos.map_tax(tax, product, partner)
            compute_vals = tax.compute_all(self.price_unit * (1 - (self.discount or 0.0) / 100.0),
                                           self.analytic_account_id.currency_id, quantity, product, partner)['taxes']
            if compute_vals:
                val += compute_vals[0].get('amount', 0)
        return val


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _recompute_tax_lines(self, recompute_tax_base_amount=False):
        """ Compute the dynamic tax lines of the journal entry.

        :param lines_map: The line_ids dispatched by type containing:
            * base_lines: The lines having a tax_ids set.
            * tax_lines: The lines having a tax_line_id set.
            * terms_lines: The lines generated by the payment terms of the invoice.
            * rounding_lines: The cash rounding lines of the invoice.
        """
        self.ensure_one()
        in_draft_mode = self != self._origin

        def _serialize_tax_grouping_key(grouping_dict):
            """ Serialize the dictionary values to be used in the taxes_map.
            :param grouping_dict: The values returned by '_get_tax_grouping_key_from_tax_line' or '_get_tax_grouping_key_from_base_line'.
            :return: A string representing the values.
            """
            return '-'.join(str(v) for v in grouping_dict.values())

        def _compute_base_line_taxes(base_line):
            """ Compute taxes amounts both in company currency / foreign currency as the ratio between
            amount_currency & balance could not be the same as the expected currency rate.
            The 'amount_currency' value will be set on compute_all(...)['taxes'] in multi-currency.
            :param base_line:   The account.move.line owning the taxes.
            :return:            The result of the compute_all method.
            """
            move = base_line.move_id

            if move.is_invoice(include_receipts=True):
                sign = -1 if move.is_inbound() else 1
                quantity = base_line.quantity
                if base_line.currency_id:
                    price_unit_foreign_curr = sign * base_line.price_unit * (1 - (base_line.discount / 100.0))
                    price_unit_comp_curr = base_line.currency_id._convert(price_unit_foreign_curr,
                                                                          move.company_id.currency_id, move.company_id,
                                                                          move.date)
                else:
                    price_unit_foreign_curr = 0.0
                    price_unit_comp_curr = sign * base_line.price_unit * (1 - (base_line.discount / 100.0))
            else:
                quantity = 1.0
                price_unit_foreign_curr = base_line.amount_currency
                price_unit_comp_curr = base_line.balance

            balance_taxes_res = base_line.tax_ids._origin.compute_all(
                price_unit_comp_curr,
                currency=base_line.company_currency_id,
                quantity=quantity * base_line.duration,
                product=base_line.product_id,
                partner=base_line.partner_id,
                is_refund=self.type in ('out_refund', 'in_refund'),
            )

            if base_line.currency_id:
                # Multi-currencies mode: Taxes are computed both in company's currency / foreign currency.
                amount_currency_taxes_res = base_line.tax_ids._origin.compute_all(
                    price_unit_foreign_curr,
                    currency=base_line.currency_id,
                    quantity=quantity,
                    product=base_line.product_id,
                    partner=base_line.partner_id,
                    is_refund=self.type in ('out_refund', 'in_refund'),
                )
                for b_tax_res, ac_tax_res in zip(balance_taxes_res['taxes'], amount_currency_taxes_res['taxes']):
                    tax = self.env['account.tax'].browse(b_tax_res['id'])
                    b_tax_res['amount_currency'] = ac_tax_res['amount']

                    # A tax having a fixed amount must be converted into the company currency when dealing with a
                    # foreign currency.
                    if tax.amount_type == 'fixed':
                        b_tax_res['amount'] = base_line.currency_id._convert(b_tax_res['amount'],
                                                                             move.company_id.currency_id,
                                                                             move.company_id, move.date)

            return balance_taxes_res

        taxes_map = {}

        # ==== Add tax lines ====
        to_remove = self.env['account.move.line']
        for line in self.line_ids.filtered('tax_repartition_line_id'):
            grouping_dict = self._get_tax_grouping_key_from_tax_line(line)
            grouping_key = _serialize_tax_grouping_key(grouping_dict)
            if grouping_key in taxes_map:
                # A line with the same key does already exist, we only need one
                # to modify it; we have to drop this one.
                to_remove += line
            else:
                taxes_map[grouping_key] = {
                    'tax_line': line,
                    'balance': 0.0,
                    'amount_currency': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                }
        self.line_ids -= to_remove

        # ==== Mount base lines ====
        for line in self.line_ids.filtered(lambda line: not line.tax_repartition_line_id):
            # Don't call compute_all if there is no tax.
            if not line.tax_ids:
                line.tag_ids = [(5, 0, 0)]
                continue

            compute_all_vals = _compute_base_line_taxes(line)

            # Assign tags on base line
            line.tag_ids = compute_all_vals['base_tags']

            tax_exigible = True
            for tax_vals in compute_all_vals['taxes']:
                grouping_dict = self._get_tax_grouping_key_from_base_line(line, tax_vals)
                grouping_key = _serialize_tax_grouping_key(grouping_dict)

                tax_repartition_line = self.env['account.tax.repartition.line'].browse(
                    tax_vals['tax_repartition_line_id'])
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id

                if tax.tax_exigibility == 'on_payment':
                    tax_exigible = False

                taxes_map_entry = taxes_map.setdefault(grouping_key, {
                    'tax_line': None,
                    'balance': 0.0,
                    'amount_currency': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                })
                taxes_map_entry['balance'] += tax_vals['amount']
                taxes_map_entry['amount_currency'] += tax_vals.get('amount_currency', 0.0)
                taxes_map_entry['tax_base_amount'] += tax_vals['base']
                taxes_map_entry['grouping_dict'] = grouping_dict
            line.tax_exigible = tax_exigible

        # ==== Process taxes_map ====
        for taxes_map_entry in taxes_map.values():
            # Don't create tax lines with zero balance.
            if self.currency_id.is_zero(taxes_map_entry['balance']) and self.currency_id.is_zero(
                    taxes_map_entry['amount_currency']):
                taxes_map_entry['grouping_dict'] = False

            tax_line = taxes_map_entry['tax_line']
            tax_base_amount = -taxes_map_entry['tax_base_amount'] if self.is_inbound() else taxes_map_entry[
                'tax_base_amount']

            if not tax_line and not taxes_map_entry['grouping_dict']:
                continue
            elif tax_line and recompute_tax_base_amount:
                tax_line.tax_base_amount = tax_base_amount
            elif tax_line and not taxes_map_entry['grouping_dict']:
                # The tax line is no longer used, drop it.
                self.line_ids -= tax_line
            elif tax_line:
                tax_line.update({
                    'amount_currency': taxes_map_entry['amount_currency'],
                    'debit': taxes_map_entry['balance'] > 0.0 and taxes_map_entry['balance'] or 0.0,
                    'credit': taxes_map_entry['balance'] < 0.0 and -taxes_map_entry['balance'] or 0.0,
                    'tax_base_amount': tax_base_amount,
                })
            else:
                create_method = in_draft_mode and self.env['account.move.line'].new or self.env[
                    'account.move.line'].create
                tax_repartition_line_id = taxes_map_entry['grouping_dict']['tax_repartition_line_id']
                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_repartition_line_id)
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id
                tax_line = create_method({
                    'name': tax.name,
                    'move_id': self.id,
                    'partner_id': line.partner_id.id,
                    'company_id': line.company_id.id,
                    'company_currency_id': line.company_currency_id.id,
                    'quantity': 1.0,
                    'date_maturity': False,
                    'amount_currency': taxes_map_entry['amount_currency'],
                    'debit': taxes_map_entry['balance'] > 0.0 and taxes_map_entry['balance'] or 0.0,
                    'credit': taxes_map_entry['balance'] < 0.0 and -taxes_map_entry['balance'] or 0.0,
                    'tax_base_amount': tax_base_amount,
                    'exclude_from_invoice_tab': True,
                    'tax_exigible': tax.tax_exigibility == 'on_invoice',
                    **taxes_map_entry['grouping_dict'],
                })

            if in_draft_mode:
                tax_line._onchange_amount_currency()
                tax_line._onchange_balance()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    duration = fields.Integer(string="Durée", default=1)

    def _get_price_total_and_subtotal(self, price_unit=None, quantity=None, discount=None, currency=None, product=None,
                                      partner=None, taxes=None, move_type=None):
        self.ensure_one()
        qty = quantity * self.duration if quantity else self.quantity * self.duration
        return self._get_price_total_and_subtotal_model(
            price_unit=price_unit or self.price_unit,
            quantity=qty,
            discount=discount or self.discount,
            currency=currency or self.currency_id,
            product=product or self.product_id,
            partner=partner or self.partner_id,
            taxes=taxes or self.tax_ids,
            move_type=move_type or self.move_id.type,
        )

    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes,
                                            move_type):
        ''' This method is used to compute 'price_total' & 'price_subtotal'.

        :param price_unit:  The current price unit.
        :param quantity:    The current quantity.
        :param discount:    The current discount.
        :param currency:    The line's currency.
        :param product:     The line's product.
        :param partner:     The line's partner.
        :param taxes:       The applied taxes.
        :param move_type:   The type of the move.
        :return:            A dictionary containing 'price_subtotal' & 'price_total'.
        '''
        res = {}

        # Compute 'price_subtotal'.
        price_unit_wo_discount = price_unit * (1 - (discount / 100.0))
        subtotal = quantity * price_unit_wo_discount

        print(quantity)

        # Compute 'price_total'.
        if taxes:
            taxes_res = taxes._origin.compute_all(price_unit_wo_discount,
                                                  quantity=quantity, currency=currency, product=product,
                                                  partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
            print(taxes_res)
            res['price_subtotal'] = taxes_res['total_excluded']
            res['price_total'] = taxes_res['total_included']
        else:
            res['price_total'] = res['price_subtotal'] = subtotal
        # In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        print(res)
        return res

    @api.onchange('quantity', 'duration', 'discount', 'price_unit')
    def _onchange_price_subtotal(self):
        super(AccountMoveLine, self)._onchange_price_subtotal()


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    partner_id = fields.Many2one('res.partner', string='Customer', tracking=10, index=True,
                                 domain="[('contact_type', 'in', ['prospect', 'customer'])]",
                                 help="Linked partner (optional). Usually created when converting the lead. You can find a partner by its Name, TIN, Email or Internal Reference.")

    contact = fields.Many2one('res.partner', domain="[('company_type', '=', 'person'), ('parent_id', '=', partner_id)]")
    company_type = fields.Selection([
        ('person', 'Personne'),
        ('company', 'Compagnie'),
    ], related='partner_id.company_type')
    campaign_name = fields.Char(string="Campagne")
    is_robot = fields.Boolean(string="Créé par webmecanik", default=False)

    @api.model
    def create(self, vals_list):
        record = super(CrmLead, self).create(vals_list)
        if self.is_robot:
            if self.partner_id and self.partner_id.user_id:
                self.user_id = self.partner_id.user_id

            elif self.contact and self.contact.parent_id.user_id:
                self.user_id = self.contact.parent_id.user_id

        return record
