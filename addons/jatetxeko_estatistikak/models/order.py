# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime

class Eskaera(models.Model):
    _name = "jatetxeko.eskaera"
    _description = "Eskaera"
    _order = "date desc"

    external_id = fields.Integer(string="Kanpo ID")
    name = fields.Char(string="Eskaera Zenbakia", required=True, copy=False, default=lambda self: self._generate_name())
    date = fields.Datetime(string="Data", required=True, default=fields.Datetime.now)
    day_of_month = fields.Integer(string="Hilabeteko eguna", compute="_compute_day_of_month", store=True, index=True)
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
        """Eskaera-zenbaki bakarra sortu"""
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

    @api.depends("date")
    def _compute_day_of_month(self):
        for record in self:
            record.day_of_month = record.date.day if record.date else False

    def action_confirm(self):
        """Eskaera berretsi"""
        self.write({'state': 'confirmed'})

    def action_pay(self):
        """Eskaera ordainduta bezala markatu"""
        self.write({'state': 'paid'})

    def action_draft(self):
        """Eskaera zirriborrora itzuli"""
        self.write({'state': 'draft'})

    @api.model
    def get_busiest_day_of_month(self, year=None):
        target_year = int(year) if year else fields.Datetime.now().year
        date_from = datetime(target_year, 1, 1)
        date_to = datetime(target_year + 1, 1, 1)

        groups = self.read_group(
            [('date', '>=', date_from), ('date', '<', date_to)],
            ['__count'],
            ['date:day'],
            lazy=False,
        )

        counts_by_day = {}
        for g in groups:
            date_key = g.get('date:day')
            if not date_key:
                continue
            date_str = str(date_key)[:10]
            try:
                day = int(date_str.split('-')[2])
            except Exception:
                continue
            counts_by_day[day] = counts_by_day.get(day, 0) + g.get('__count', 0)

        if not counts_by_day:
            return {
                'year': target_year,
                'best_days': [],
                'max_count': 0,
                'by_day': [],
            }

        max_count = max(counts_by_day.values())
        best_days = sorted([d for d, c in counts_by_day.items() if c == max_count])
        by_day = [{'day': d, 'count': counts_by_day[d]} for d in sorted(counts_by_day.keys())]

        return {
            'year': target_year,
            'best_days': best_days,
            'max_count': max_count,
            'by_day': by_day,
        }


class HilabetekoEgunJendetsuena(models.Model):
    _name = "jatetxeko.stats.month_busiest_day"
    _description = "Hilabeteko Egun Jendetsuena (Hilabetez)"
    _auto = False
    _rec_name = "hilabetea"

    hilabetea = fields.Char(string="Hilabetea", readonly=True)
    egun_jendetsuena = fields.Date(string="Egun jendetsuena", readonly=True)
    eskaera_kopurua = fields.Integer(string="Eskaerak", readonly=True)

    def init(self):
        self._cr.execute("DROP VIEW IF EXISTS jatetxeko_stats_month_busiest_day CASCADE")
        self._cr.execute("""
            CREATE OR REPLACE VIEW jatetxeko_stats_month_busiest_day AS (
                WITH day_counts AS (
                    SELECT
                        date_trunc('month', date) AS month_start,
                        date::date AS day,
                        COUNT(*) AS eskaera_kopurua
                    FROM jatetxeko_eskaera
                    WHERE date IS NOT NULL
                    GROUP BY 1, 2
                ),
                busiest AS (
                    SELECT DISTINCT ON (month_start)
                        month_start,
                        day,
                        eskaera_kopurua
                    FROM day_counts
                    ORDER BY month_start, eskaera_kopurua DESC, day ASC
                )
                SELECT
                    ROW_NUMBER() OVER (ORDER BY month_start) AS id,
                    to_char(month_start, 'YYYY-MM') AS hilabetea,
                    day AS egun_jendetsuena,
                    eskaera_kopurua
                FROM busiest
            )
        """)


class EskaeraLine(models.Model):
    _name = "jatetxeko.eskaera.line"
    _description = "Eskaera Lerroa"

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
