# -*- coding: utf-8 -*-
from odoo import models, fields, api

class Eskaera(models.Model):
    _name = "jatetxeko.eskaera"
    _description = "Eskaera (Order)"
    _order = "date desc"

    external_id = fields.Integer(string="Kanpo ID")
    name = fields.Char(string="Eskaera Zenbakia", required=True, copy=False, default=lambda self: self._generate_name())
    date = fields.Datetime(string="Data", required=True, default=fields.Datetime.now)
    zerbitzaria_id = fields.Many2one("jatetxeko.zerbitzaria", string="Zerbitzaria", ondelete="set null")
    mahia_id = fields.Many2one("jatetxeko.mahia", string="Mahia", ondelete="set null")
    line_ids = fields.One2many("jatetxeko.eskaera.line", "eskaera_id", string="Lerroak")
    subtotal = fields.Float(string="Azpikopurua", compute="_compute_totals", store=True)
    discount_id = fields.Many2one("jatetxeko.deskontuak", string="Deskuntu Kodea")
    discount_percent = fields.Float(related="discount_id.percentage", string="Deskuntu Ehunekoa")
    discount_amount = fields.Float(string="Deskuntu Kantitatea", compute="_compute_totals", store=True)
    total_amount = fields.Float(string="Guztizkoa", compute="_compute_totals", store=True)
    state = fields.Selection([
        ("draft", "Zirriborroa"),
        ("confirmed", "Berretsia"),
        ("paid", "Ordainduta"),
    ], string="Egoera", default="draft")

    @api.model
    def _generate_name(self):
        """Generate unique order number"""
        last_order = self.search([], order='id desc', limit=1)
        if last_order:
            return f"ESK-{int(last_order.name.split('-')[1]) + 1:06d}"
        return "ESK-000001"

    @api.depends("line_ids", "discount_id")
    def _compute_totals(self):
        for record in self:
            subtotal = sum(line.price_subtotal for line in record.line_ids)
            record.subtotal = subtotal
            if record.discount_id:
                record.discount_amount = subtotal * (record.discount_id.percentage / 100)
            else:
                record.discount_amount = 0.0
            record.total_amount = subtotal - record.discount_amount

    def action_confirm(self):
        """Confirm the order"""
        self.write({'state': 'confirmed'})

    def action_pay(self):
        """Mark order as paid"""
        self.write({'state': 'paid'})

    def action_draft(self):
        """Reset order to draft"""
        self.write({'state': 'draft'})


class EskaeraLine(models.Model):
    _name = "jatetxeko.eskaera.line"
    _description = "Eskaera Lerroa (Order Line)"

    eskaera_id = fields.Many2one("jatetxeko.eskaera", string="Eskaera", ondelete="cascade")
    platera_id = fields.Many2one("jatetxeko.platera", string="Platera")
    quantity = fields.Integer(string="Kopurua", default=1)
    price_unit = fields.Float(string="Prezio Unitarioa")
    price_subtotal = fields.Float(string="Azpikopurua", compute="_compute_subtotal", store=True)

    @api.depends("quantity", "price_unit")
    def _compute_subtotal(self):
        for record in self:
            record.price_subtotal = record.quantity * record.price_unit

    @api.onchange("platera_id")
    def _onchange_platera(self):
        if self.platera_id:
            self.price_unit = self.platera_id.price