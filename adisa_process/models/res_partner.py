# -*- coding: utf-8 -*-
import urllib.request as http
import base64
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.onchange('linkedin_logo')
    def onchange_image(self, context=None):
        link = self.linkedin_logo
        # photo = base64.encodestring(http.urlopen(link).read())
        # self.image_1920 = photo
        # val = {
        #     'image_1920': photo,
        # }
        # return {'value': val}

    society_nature = fields.Selection([('prospect', 'Prospect'),
                                       ('customer', 'Client'),
                                       ('prescript', 'Prescripteur'),
                                       ('suppliers', 'Fournisseur')], 'Nature société', default='prospect')

    contact_nature = fields.Selection([('prospect', 'Prospect'),
                                       ('freelance', 'Freelance'),
                                       ('customer', 'Client'),
                                       ('suppliers', 'Fournisseur'),
                                       ('prescript', 'Prescripteur'),
                                       ('employee', 'Employé')], 'Nature contact', default='prospect')
    society_type = fields.Selection([('adm', 'ADM'),
                                     ('ge', 'Grande Entreprise'),
                                     ('institute', 'Institut'),
                                     ('ong', 'ONG'),
                                     ('pme', 'PME')], 'Type société')
    society_category = fields.Many2one('res.partner.society.category', 'Categorie société')
    activity = fields.Many2one('res.partner.activity', 'Activité')
    function_2 = fields.Many2one('res.partner.function', 'Fonction')
    company_type = fields.Selection(string='Company Type',
                                    selection=[('person', 'Individual'), ('company', 'Company')],
                                    compute='_compute_company_type', inverse='_write_company_type', store=True)
    # parent_id = fields.Many2one('res.partner', string='Related Company',
    #                             domain="[('company_type', '=', 'company')", index=True)
    linkedin = fields.Char(string="LinkedIn")
    linkedin_logo = fields.Char('image url', help='Automatically sanitized HTML contents')
    # personal informations
    fax = fields.Char(string="Fax")
    points = fields.Char(string="Points")
    twitter = fields.Char(string="Twitter")
    facebook = fields.Char(string="Facebook")
    # skype = fields.Char(string="Skype")
    instagram = fields.Char(string="Instagram")
    personal_addr = fields.Char(string="Adresse personelle 1")
    personal_addr2 = fields.Char(string="Adresse personelle 2")
    personal_postal = fields.Char(string="Adresse postale personelle")
    postal = fields.Char(string="Adresse postale")
    commune = fields.Char(string="Commune")
    personal_city = fields.Char(string="Ville 2")
    personal_state = fields.Many2one('res.country.state', string="État 2")
    personal_code_postal = fields.Char(string="Code postal 2")
    personal_country = fields.Many2one('res.country', string="Pays 2")
    mobile2 = fields.Char(string="Mobile 2")
    personal_email = fields.Char('Pers. Email')
    source = fields.Char(string="Source")
    first_name = fields.Char(string="Prénom")
    last_name = fields.Char(string="Nom")
    # society informations
    society_desc = fields.Text(string="Description")
    nbr_employee = fields.Selection([('small', '1-10'),
                                     ('medium', '11-50'),
                                     ('large', '51-200'),
                                     ('extra-large', '201-500')], string="Nbr employés")

    @api.onchange('parent_id')
    def _get_vendor(self):
        if self.parent_id and self.parent_id.user_id:
            self.user_id = self.parent_id.user_id


class ResPartnerFunction(models.Model):
    _name = 'res.partner.function'

    name = fields.Char('Name', required=True)

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Choose another value - it has to be unique!')
    ]


class ResPartnerType(models.Model):
    _name = 'res.partner.type'

    name = fields.Char('Name', required=True)

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Choose another value - it has to be unique!')
    ]


class ResPartnerCategory(models.Model):
    _name = 'res.partner.society.category'

    name = fields.Char('Name', required=True)

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Choose another value - it has to be unique!')
    ]


class ResPartnerActivity(models.Model):
    _name = 'res.partner.activity'

    name = fields.Char('Name', required=True)
    industry_id = fields.Many2one('res.partner.industry', 'Secteur', ondelete='cascade', required=True)

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Choose another value - it has to be unique!')
    ]
