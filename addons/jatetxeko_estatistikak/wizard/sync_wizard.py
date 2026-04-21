# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SyncWizard(models.TransientModel):
    _name = "jatetxeko.sync.wizard"
    _description = "API Sinkronizazio Wizard"

    sync_type = fields.Selection([
        ('full', 'Sinkronizazio osoa (dena)'),
        ('masters', 'Datu maisuak (zerbitzariak, platerak, mahiak)'),
        ('orders', 'Eskaerak soilik'),
        ('push_workers', 'Langileak APIra bidali'),
    ], string='Mota', default='masters', required=True)

    date_from = fields.Datetime(string='Data-tik', help='Eskaerak sinkronizatzeko hasiera data')

    def action_sync(self):
        """Execute the sync operation"""
        self.ensure_one()
        sync_api = self.env['jatetxeko.api.sync']

        try:
            if self.sync_type == 'full':
                result = sync_api.sync_all()
            elif self.sync_type == 'orders':
                date_str = self.date_from.isoformat() if self.date_from else None
                result = sync_api.sync_orders(date_str)
                result = {'status': 'success', 'records_synced': result}
            elif self.sync_type == 'push_workers':
                result = sync_api.push_all_workers_to_api()
                if result.get('errors'):
                    msg = _("%s langile bidali dira. Erroreak: %s") % (result.get('pushed', 0), ', '.join(result['errors']))
                else:
                    msg = _("%s langile bidali dira APIra.") % result.get('pushed', 0)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Langileak APIra'),
                        'message': msg,
                        'type': 'success' if not result.get('errors') else 'warning',
                        'sticky': False,
                    }
                }
            else:  # masters
                result = sync_api.sync_masters()

            if result.get('status') == 'failed':
                raise UserError(_("Sinkronizazio errorea: %s") % result.get('error', 'Ezezaguna'))

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sinkronizazioa'),
                    'message': _("Sinkronizazioa amaitu da. %s erregistro prozesatu dira.") % result.get('records_synced', 0),
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            raise UserError(_("Sinkronizazio errorea: %s") % str(e))