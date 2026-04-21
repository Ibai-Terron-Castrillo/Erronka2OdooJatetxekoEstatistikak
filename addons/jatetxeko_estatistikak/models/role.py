# -*- coding: utf-8 -*-
from odoo import models, fields


class Rola(models.Model):
    _name = "jatetxeko.rola"
    _description = "Rola (Role)"

    name = fields.Char(string="Izena", required=True)
    external_id = fields.Integer(string="Kanpo ID", help="C# API-ko ID")
    active = fields.Boolean(string="Aktibo", default=True)

    def unlink(self):
        """
        Manually clear references in Zerbitzaria (Server) before deleting the Role
        to bypass database constraint if module is not fully updated.
        Using sudo() to ensure we have permission to clear the field.
        """
        for record in self:
            # Find servers using this role
            servers = self.env['jatetxeko.zerbitzaria'].sudo().search([('role_id', '=', record.id)])
            if servers:
                # Clear the role_id
                servers.write({'role_id': False})
        return super(Rola, self).unlink()