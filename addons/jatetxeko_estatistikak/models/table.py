# -*- coding: utf-8 -*-
from odoo import models, fields

class Mahia(models.Model):
    _name = "jatetxeko.mahia"
    _description = "Mahia (Table)"

    name = fields.Char(string="Mahia Zenbakia", required=True)
    external_id = fields.Integer(string="Kanpo ID")
    capacity = fields.Integer(string="Edukiera")
    active = fields.Boolean(string="Aktibo", default=True)
    order_ids = fields.One2many("jatetxeko.eskaera", "mahia_id", string="Eskaerak")

    def unlink(self):
        """
        Manually clear references in Eskaera (Order) before deleting the Table
        to bypass database constraint if module is not fully updated.
        """
        for record in self:
            # Find orders using this table
            orders = self.env['jatetxeko.eskaera'].search([('mahia_id', '=', record.id)])
            if orders:
                # Clear the mahia_id
                orders.write({'mahia_id': False})
        return super(Mahia, self).unlink()