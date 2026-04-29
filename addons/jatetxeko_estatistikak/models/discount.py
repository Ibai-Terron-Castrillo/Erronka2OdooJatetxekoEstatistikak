# -*- coding: utf-8 -*-
from odoo import models, fields, api
import random
import string


class Deskontuak(models.Model):
    _name = "jatetxeko.deskontuak"
    _description = "Deskontuak"

    name = fields.Char(
        string="Kodea",
        required=True,
        copy=False,
        default=lambda self: self._generate_code()
    )
    percentage = fields.Float(string="Ehunekoa", required=True)
    description = fields.Text(string="Deskribapena")
    active = fields.Boolean(string="Aktibo", default=True)
    usage_limit = fields.Integer(
        string="Erabilera Muga",
        default=0,
        help="0 = mugagabea"
    )
    usage_count = fields.Integer(string="Erabilera Kopurua", default=0)
    valid_from = fields.Date(string="Balio-hasiera")
    valid_until = fields.Date(string="Balio-bukaera")

    _sql_constraints = [
        (
            'jatetxeko_deskontuak_name_unique',
            'unique(name)',
            'Deskuntu kode hori dagoeneko existitzen da.'
        )
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name'):
                vals['name'] = self._normalize_code(vals['name'])
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('name'):
            vals['name'] = self._normalize_code(vals['name'])
        return super().write(vals)

    def unlink(self):
        """
        Deskuntua ezabatu aurretik, Eskaeretan (jatetxeko.eskaera) dauden erreferentziak eskuz garbitu,
        modulua guztiz eguneratuta ez badago datu-baseko murrizketak saihesteko.
        """
        for record in self:
            # Deskuntu hau erabiltzen duten eskaerak bilatu
            orders = self.env['jatetxeko.eskaera'].search([('discount_id', '=', record.id)])
            if orders:
                # discount_id eremua garbitu
        Clear discount references before deleting a discount code.
        """
        for record in self:
            orders = self.env['jatetxeko.eskaera'].sudo().search([
                ('discount_id', '=', record.id)
            ])
            if orders:
                orders.write({'discount_id': False})
        return super(Deskontuak, self).unlink()

    @api.model
    def _generate_code(self):
        """Ausazko 8 karaktereko deskontu-kodea sortu"""
        """Generate random 8-character discount code."""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    @api.model
    def _normalize_code(self, code):
        if code is None:
            return ''
        return str(code).strip().upper()

    @api.model
    def validate_code(self, code):
        """Deskontu-kodea balioztatu eta, baliozkoa bada, ehunekoa itzuli"""
        discount = self.search([('name', '=', code), ('active', '=', True)], limit=1)
        """Validate a discount code and return its percentage if valid."""
        normalized_code = self._normalize_code(code)

        if not normalized_code:
            return {'valid': False, 'message': 'Kodea beharrezkoa da'}

        discount = self.search([
            ('name', '=', normalized_code),
            ('active', '=', True)
        ], limit=1)

        if not discount:
            return {'valid': False, 'message': 'Kodea ez da aurkitu'}

        today = fields.Date.today()

        if discount.valid_from and discount.valid_from > today:
            return {'valid': False, 'message': 'Kodea oraindik ez da baliozkoa'}

        if discount.valid_until and discount.valid_until < today:
            return {'valid': False, 'message': 'Kodea iraungi da'}

        if discount.usage_limit > 0 and discount.usage_count >= discount.usage_limit:
            return {'valid': False, 'message': 'Kodea jada erabili da'}

        return {
            'valid': True,
            'percentage': float(discount.percentage),
            'code_id': discount.id
        }

    def use_code(self):
        """Erabilera-kopurua handitu"""
        self.ensure_one()
        self.usage_count += 1
        """Increment usage count."""
        self.ensure_one()
        self.write({'usage_count': self.usage_count + 1})
