# -*- coding: utf-8 -*-
from odoo import models, api
from datetime import datetime, timedelta
from collections import defaultdict
import io
import base64

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class ReportStatistics(models.AbstractModel):
    _name = 'report.jatetxeko_estatistikak.statistics_report'
    _description = 'Jatetxeko Estatistika Txostena'

    def _generate_bar_chart(self, labels, values, title, xlabel, ylabel):
        """Generate a bar chart and return as base64"""
        if not HAS_MATPLOTLIB:
            return None

        fig, ax = plt.subplots(figsize=(8, 4))

        # Create bars
        bars = ax.bar(labels, values, color='#3498db')

        # Customize
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)

        # Rotate x labels if needed
        if len(labels) > 5:
            plt.xticks(rotation=45, ha='right')

        # Add value labels on bars
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax.annotate(f'{val:.0f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=9)

        plt.tight_layout()

        # Save to buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        plt.close()

        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    def _generate_line_chart(self, labels, values, title, xlabel, ylabel):
        """Generate a line chart and return as base64"""
        if not HAS_MATPLOTLIB:
            return None

        fig, ax = plt.subplots(figsize=(8, 4))

        # Create line
        ax.plot(labels, values, marker='o', color='#2ecc71', linewidth=2, markersize=6)

        # Customize
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)

        # Rotate x labels if needed
        if len(labels) > 5:
            plt.xticks(rotation=45, ha='right')

        # Add grid
        ax.grid(True, linestyle='--', alpha=0.7)

        plt.tight_layout()

        # Save to buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        plt.close()

        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    def _generate_pie_chart(self, labels, values, title):
        """Generate a pie chart and return as base64"""
        if not HAS_MATPLOTLIB:
            return None

        fig, ax = plt.subplots(figsize=(6, 6))

        # Colors
        colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#34495e', '#e67e22']

        # Create pie
        wedges, texts, autotexts = ax.pie(values, labels=labels, autopct='%1.1f%%',
                                          colors=colors[:len(labels)], startangle=90)

        ax.set_title(title, fontsize=12, fontweight='bold')

        plt.tight_layout()

        # Save to buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        plt.close()

        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    @api.model
    def _get_report_values(self, docids, data=None):
        """Prepare data for the statistics report"""
        docs = self.env['jatetxeko.eskaera'].browse(docids) if docids else self.env['jatetxeko.eskaera'].search([])

        # Date range from data or default to last 30 days
        date_from = data.get('date_from') if data else None
        date_to = data.get('date_to') if data else None

        if not date_from:
            date_from = datetime.now() - timedelta(days=30)
        if not date_to:
            date_to = datetime.now()

        # Filter orders by date
        domain = [('date', '>=', date_from), ('date', '<=', date_to)]
        orders = self.env['jatetxeko.eskaera'].search(domain)

        # Statistics per server (zerbitzaria)
        server_stats = defaultdict(lambda: {'total': 0, 'count': 0, 'name': ''})
        for order in orders:
            if order.zerbitzaria_id:
                server_id = order.zerbitzaria_id.id
                server_stats[server_id]['total'] += order.total_amount
                server_stats[server_id]['count'] += 1
                server_stats[server_id]['name'] = order.zerbitzaria_id.name

        # Statistics per dish (platera)
        dish_stats = defaultdict(lambda: {'quantity': 0, 'total': 0, 'name': ''})
        for order in orders:
            for line in order.line_ids:
                if line.platera_id:
                    dish_id = line.platera_id.id
                    dish_stats[dish_id]['quantity'] += line.quantity
                    dish_stats[dish_id]['total'] += line.price_subtotal
                    dish_stats[dish_id]['name'] = line.platera_id.name

        # Statistics per day of week
        day_stats = defaultdict(lambda: {'total': 0, 'count': 0})
        day_names = ['Astelehena', 'Asteartea', 'Asteazkena', 'Osteguna', 'Ostirala', 'Larunbata', 'Igandea']
        day_names_short = ['Astel', 'Astear', 'Astaz', 'Oste', 'Osti', 'Lar', 'Igan']
        for order in orders:
            if order.date:
                day_idx = order.date.weekday()
                day_stats[day_idx]['total'] += order.total_amount
                day_stats[day_idx]['count'] += 1

        # Monthly statistics
        month_stats = defaultdict(lambda: {'total': 0, 'count': 0})
        for order in orders:
            if order.date:
                month_key = order.date.strftime('%Y-%m')
                month_stats[month_key]['total'] += order.total_amount
                month_stats[month_key]['count'] += 1

        # Overall summary
        total_revenue = sum(order.total_amount for order in orders)
        total_orders = len(orders)
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

        # Generate charts
        charts = {}

        # Server revenue bar chart
        if server_stats:
            server_names = [s['name'][:10] for s in server_stats.values()]
            server_totals = [s['total'] for s in server_stats.values()]
            charts['server_revenue'] = self._generate_bar_chart(
                server_names, server_totals,
                'Zerbitzarien Diru-sarrera', 'Zerbitzaria', 'Guztizkoa (€)'
            )

        # Dish quantity bar chart (top 10)
        if dish_stats:
            sorted_dishes = sorted(dish_stats.values(), key=lambda x: x['quantity'], reverse=True)[:10]
            dish_names = [d['name'][:10] for d in sorted_dishes]
            dish_quantities = [d['quantity'] for d in sorted_dishes]
            charts['dish_quantity'] = self._generate_bar_chart(
                dish_names, dish_quantities,
                'Plater Popularrak', 'Platera', 'Kopurua'
            )

        # Day of week line chart
        day_totals = [day_stats.get(i, {}).get('total', 0) for i in range(7)]
        charts['day_of_week'] = self._generate_line_chart(
            day_names_short, day_totals,
            'Asteko Egunen Araberako Salmentak', 'Eguna', 'Guztizkoa (€)'
        )

        # Monthly line chart
        if month_stats:
            sorted_months = sorted(month_stats.keys())
            month_totals = [month_stats[m]['total'] for m in sorted_months]
            charts['monthly'] = self._generate_line_chart(
                sorted_months, month_totals,
                'Hileko Salmentak', 'Hilabetea', 'Guztizkoa (€)'
            )

        # Server pie chart (revenue distribution)
        if server_stats and len(server_stats) > 1:
            server_names_pie = [s['name'][:15] for s in server_stats.values()]
            server_totals_pie = [s['total'] for s in server_stats.values()]
            charts['server_pie'] = self._generate_pie_chart(
                server_names_pie, server_totals_pie,
                'Zerbitzarien Banaketa'
            )

        return {
            'doc_ids': docids,
            'doc_model': 'jatetxeko.eskaera',
            'docs': docs,
            'data': data or {},
            'date_from': date_from,
            'date_to': date_to,
            'server_stats': dict(server_stats),
            'dish_stats': dict(dish_stats),
            'day_stats': dict(day_stats),
            'day_names': day_names,
            'month_stats': dict(month_stats),
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'avg_order_value': avg_order_value,
            'datetime': datetime,
            'charts': charts,
            'has_matplotlib': HAS_MATPLOTLIB,
        }