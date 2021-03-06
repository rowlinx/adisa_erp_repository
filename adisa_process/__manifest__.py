# -*- coding: utf-8 -*-
{
    'name': "adisa_process",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Adisa",
    'website': "https://www.adisa.digital",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'purchase', 'crm', 'sale_subscription'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'templates/cron.xml',
        'wizard/customer_portfolio_wizard_view.xml',
        'wizard/lead_transfer_wizard_view.xml',
        'views/views.xml',
        'views/res_partner.xml',
        'views/res_config_setting_view.xml',
        # 'views/templates.xml',
        'report/sale.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
