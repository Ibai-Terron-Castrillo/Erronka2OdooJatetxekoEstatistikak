# -*- coding: utf-8 -*-
from odoo import models, fields, api

class Platera(models.Model):
    _name = "jatetxeko.platera"
    _description = "Platera"

    name = fields.Char(string="Izena", required=True)
    external_id = fields.Integer(string="Kanpo ID")
    price = fields.Float(string="Prezioa", required=True)
    category = fields.Char(string="Kategoria")
    active = fields.Boolean(string="Aktibo", default=True)
    order_line_ids = fields.One2many("jatetxeko.eskaera.line", "platera_id", string="Eskaera Lerroak")
    total_ordered = fields.Integer(string="Eskaera Kopurua", compute="_compute_total_ordered")

    def unlink(self):
        """
        Platera ezabatu aurretik, Eskaera Lerroetan (jatetxeko.eskaera.line) dauden erreferentziak eskuz garbitu,
        modulua guztiz eguneratuta ez badago datu-baseko murrizketak saihesteko.
        """
        for record in self:
            # Platera hau erabiltzen duten eskaera lerroak bilatu
            lines = self.env['jatetxeko.eskaera.line'].search([('platera_id', '=', record.id)])
            if lines:
                # platera_id eremua garbitu
                lines.write({'platera_id': False})
        return super(Platera, self).unlink()

    @api.depends("order_line_ids")
    def _compute_total_ordered(self):
        for record in self:
            record.total_ordered = sum(record.order_line_ids.mapped("quantity"))
