# -*- coding: utf-8 -*-
from odoo import models, fields, api
import random
import string
import unicodedata


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
            orders = self.env['jatetxeko.eskaera'].sudo().search([
                ('discount_id', '=', record.id)
            ])
            if orders:
                orders.write({'discount_id': False})
        return super(Deskontuak, self).unlink()

    @api.model
    def _generate_code(self):
        """Ausazko 8 karaktereko deskontu-kodea sortu"""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    @api.model
    def _normalize_code(self, code):
        if code is None:
            return ''

        normalized = unicodedata.normalize('NFKC', str(code))
        return ''.join(
            character
            for character in normalized
            if not character.isspace()
            and unicodedata.category(character) not in ('Cc', 'Cf')
        ).upper()

    @api.model
    def validate_code(self, code):
        """Deskontu-kodea balioztatu eta, baliozkoa bada, ehunekoa itzuli"""
        normalized_code = self._normalize_code(code)

        if not normalized_code:
            return {'valid': False, 'message': 'Kodea beharrezkoa da'}

        discount = self.search([
            ('name', '=', normalized_code),
            ('active', '=', True)
        ], limit=1)

        if not discount:
            discount = self.browse()
            for candidate in self.search([('active', '=', True)]):
                if self._normalize_code(candidate.name) == normalized_code:
                    discount = candidate
                    break

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
        self.write({'usage_count': self.usage_count + 1})
