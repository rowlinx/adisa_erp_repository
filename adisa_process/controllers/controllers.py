# -*- coding: utf-8 -*-
# from odoo import http


# class AdisaProcess(http.Controller):
#     @http.route('/adisa_process/adisa_process/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/adisa_process/adisa_process/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('adisa_process.listing', {
#             'root': '/adisa_process/adisa_process',
#             'objects': http.request.env['adisa_process.adisa_process'].search([]),
#         })

#     @http.route('/adisa_process/adisa_process/objects/<model("adisa_process.adisa_process"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('adisa_process.object', {
#             'object': obj
#         })
