# -*- coding: utf-8 -*-
from odoo import models, fields

class SyncLog(models.Model):
    _name = "jatetxeko.sync.log"
    _description = "Sinkronizazio Log"
    _order = "create_date desc"

    name = fields.Char(string="Sinkronizazioa", default="API Sinkronizazioa")
    sync_type = fields.Selection([
        ("full", "Osoa"),
        ("partial", "Partziala"),
    ], string="Mota", default="partial")
    status = fields.Selection([
        ("success", "Arrakasta"),
        ("failed", "Hutsa"),
    ], string="Egoera")
    records_synced = fields.Integer(string="Sinkronizatutako Erregistroak")
    error_message = fields.Text(string="Errore Mezua")
    sync_date = fields.Datetime(string="Data", default=fields.Datetime.now)