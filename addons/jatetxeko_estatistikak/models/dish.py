# -*- coding: utf-8 -*-
from odoo import models, fields, api

class Platera(models.Model):
    _name = "jatetxeko.platera"
    _description = "Platera (Dish)"

    name = fields.Char(string="Izena", required=True)
    external_id = fields.Integer(string="Kanpo ID")
    price = fields.Float(string="Prezioa", required=True)
    category = fields.Char(string="Kategoria")
    active = fields.Boolean(string="Aktibo", default=True)
    order_line_ids = fields.One2many("jatetxeko.eskaera.line", "platera_id", string="Eskaera Lerroak")
    total_ordered = fields.Integer(string="Eskaera Kopurua", compute="_compute_total_ordered")

    def unlink(self):
        """
        Manually clear references in EskaeraLine before deleting the Dish
        to bypass database constraint if module is not fully updated.
        """
        for record in self:
            # Find order lines using this dish
            lines = self.env['jatetxeko.eskaera.line'].search([('platera_id', '=', record.id)])
            if lines:
                # Clear the platera_id
                lines.write({'platera_id': False})
        return super(Platera, self).unlink()

    @api.depends("order_line_ids")
    def _compute_total_ordered(self):
        for record in self:
            record.total_ordered = sum(record.order_line_ids.mapped("quantity"))