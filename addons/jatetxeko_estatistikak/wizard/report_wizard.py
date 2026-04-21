# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta


class ReportWizard(models.TransientModel):
    _name = 'jatetxeko.report.wizard'
    _description = 'Estatistika Txostena Wizard'

    date_from = fields.Date(
        string='Data Hasiera',
        required=True,
        default=lambda self: fields.Date.today() - timedelta(days=30)
    )
    date_to = fields.Date(
        string='Data Amaiera',
        required=True,
        default=lambda self: fields.Date.today()
    )

    def action_print_report(self):
        """Print the statistics report"""
        self.ensure_one()
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
        }
        return self.env.ref('jatetxeko_estatistikak.action_report_statistics_pdf').report_action(None, data=data)