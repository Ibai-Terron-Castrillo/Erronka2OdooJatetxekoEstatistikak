import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class Zerbitzaria(models.Model):
    _name = "jatetxeko.zerbitzaria"
    _description = "Zerbitzaria (Server)"

    name = fields.Char(string="Izena", required=True)
    external_id = fields.Integer(string="Kanpo ID", help="C# API-ko ID")
    active = fields.Boolean(string="Aktibo", default=True)
    # Fields for creating worker in API
    erabiltzailea = fields.Char(string="Erabiltzailea", help="Saio hasteko erabiltzaile izena")
    pasahitza = fields.Char(string="Pasahitza", help="Saio hasteko pasahitza")
    role_id = fields.Many2one("jatetxeko.rola", string="Rola", ondelete="set null", help="Langilearen rola")
    txat_baimena = fields.Boolean(string="Txat Baimena", default=True)
    erregistro_data = fields.Datetime(string="Erregistro Data", readonly=True)
    # Statistics
    order_ids = fields.One2many("jatetxeko.eskaera", "zerbitzaria_id", string="Eskaerak")
    total_orders = fields.Integer(string="Eskaera Kopurua", compute="_compute_total_orders")
    total_billing = fields.Float(string="Fakturazioa", compute="_compute_total_billing")

    def unlink(self):
        """
        Manually clear references in Eskaera (Order) before deleting the Server
        to bypass database constraint if module is not fully updated.
        Using sudo() to ensure we have permission to clear the field.
        """
        for record in self:
            # Find orders using this server
            orders = self.env['jatetxeko.eskaera'].sudo().search([('zerbitzaria_id', '=', record.id)])
            if orders:
                # Clear the zerbitzaria_id
                orders.write({'zerbitzaria_id': False})
        return super(Zerbitzaria, self).unlink()

    @api.depends("order_ids")
    def _compute_total_orders(self):
        for record in self:
            record.total_orders = len(record.order_ids)

    @api.depends("order_ids.total_amount")
    def _compute_total_billing(self):
        for record in self:
            record.total_billing = sum(record.order_ids.mapped("total_amount"))

    def action_push_to_api(self):
        """Push this worker to C# API"""
        for record in self:
            if not record.erabiltzailea or not record.pasahitza:
                raise UserError("Erabiltzailea eta pasahitza beharrezkoak dira APIra bidaltzeko.")
            self.env['jatetxeko.api.sync'].push_worker_to_api(record)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'API Sinkronizazioa',
                'message': 'Langilea ondo bidali da APIra.',
                'type': 'success',
                'sticky': False,
            }
        }

