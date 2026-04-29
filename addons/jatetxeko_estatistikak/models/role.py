# -*- coding: utf-8 -*-
from odoo import models, fields


class Rola(models.Model):
    _name = "jatetxeko.rola"
    _description = "Rola"

    name = fields.Char(string="Izena", required=True)
    external_id = fields.Integer(string="Kanpo ID", help="C# API-ko ID")
    active = fields.Boolean(string="Aktibo", default=True)

    def unlink(self):
        """
        Rola ezabatu aurretik, Zerbitzarietan (jatetxeko.zerbitzaria) dauden erreferentziak eskuz garbitu,
        modulua guztiz eguneratuta ez badago datu-baseko murrizketak saihesteko.
        sudo() erabiltzen da eremua garbitzeko baimenak ziurtatzeko.
        """
        for record in self:
            # Rola hau erabiltzen duten zerbitzariak bilatu
            servers = self.env['jatetxeko.zerbitzaria'].sudo().search([('role_id', '=', record.id)])
            if servers:
                # role_id eremua garbitu
                servers.write({'role_id': False})
        return super(Rola, self).unlink()
