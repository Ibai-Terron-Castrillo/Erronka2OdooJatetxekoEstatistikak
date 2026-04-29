# -*- coding: utf-8 -*-
from odoo import models, fields

class Mahia(models.Model):
    _name = "jatetxeko.mahia"
    _description = "Mahia"

    name = fields.Char(string="Mahia Zenbakia", required=True)
    external_id = fields.Integer(string="Kanpo ID")
    capacity = fields.Integer(string="Edukiera")
    active = fields.Boolean(string="Aktibo", default=True)
    order_ids = fields.One2many("jatetxeko.eskaera", "mahia_id", string="Eskaerak")

    def unlink(self):
        """
        Mahaia ezabatu aurretik, Eskaeretan (jatetxeko.eskaera) dauden erreferentziak eskuz garbitu,
        modulua guztiz eguneratuta ez badago datu-baseko murrizketak saihesteko.
        """
        for record in self:
            # Mahia hau erabiltzen duten eskaerak bilatu
            orders = self.env['jatetxeko.eskaera'].search([('mahia_id', '=', record.id)])
            if orders:
                # mahia_id eremua garbitu
                orders.write({'mahia_id': False})
        return super(Mahia, self).unlink()
