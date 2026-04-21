# -*- coding: utf-8 -*-
from odoo import models, fields, api
import random
import string

class Deskontuak(models.Model):
    _name = "jatetxeko.deskontuak"
    _description = "Deskontuak (Discount Codes)"

    name = fields.Char(string="Kodea", required=True, copy=False,
                       default=lambda self: self._generate_code())
    percentage = fields.Float(string="Ehunekoa", required=True)
    description = fields.Text(string="Deskribapena")
    active = fields.Boolean(string="Aktibo", default=True)
    usage_limit = fields.Integer(string="Erabilera Muga", default=0,
                                  help="0 = mugagabea")
    usage_count = fields.Integer(string="Erabilera Kopurua", default=0)
    valid_from = fields.Date(string="Balio-hasiera")
    valid_until = fields.Date(string="Balio-bukaera")

    def unlink(self):
        """
        Manually clear references in Eskaera before deleting the Discount
        to bypass database constraint if module is not fully updated.
        """
        for record in self:
            # Find orders using this discount
            orders = self.env['jatetxeko.eskaera'].search([('discount_id', '=', record.id)])
            if orders:
                # Clear the discount_id
                orders.write({'discount_id': False})
        return super(Deskontuak, self).unlink()

    @api.model
    def _generate_code(self):
        """Generate random 8-character discount code"""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    @api.model
    def validate_code(self, code):
        """Validate a discount code and return percentage if valid"""
        discount = self.search([('name', '=', code), ('active', '=', True)], limit=1)
        if not discount:
            return {'valid': False, 'message': 'Kodea ez da aurkitu'}

        today = fields.Date.today()

        if discount.valid_from and discount.valid_from > today:
            return {'valid': False, 'message': 'Kodea oraindik ez da baliozkoa'}

        if discount.valid_until and discount.valid_until < today:
            return {'valid': False, 'message': 'Kodea iraungi da'}

        if discount.usage_limit > 0 and discount.usage_count >= discount.usage_limit:
            return {'valid': False, 'message': 'Kodea jada erabili da'}

        return {'valid': True, 'percentage': discount.percentage, 'code_id': discount.id}

    def use_code(self):
        """Increment usage count"""
        self.ensure_one()
        self.usage_count += 1