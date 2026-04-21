# -*- coding: utf-8 -*-
{
    'name': 'Jatetxeko Estatistikak',
    'summary': 'Restaurant Statistics and Management',
    'description': """
        Restaurant Statistics module with C# API integration.
        Features:
        - Sync servers, dishes, tables, orders from C# API (port 5093)
        - Statistics via Graph/Pivot views
        - Discount code management with TPV API
        - Role-based access (Administrator vs Server)
    """,
    'author': 'BlueHat',
    'website': 'https://www.bluehat.com',
    'category': 'Restaurant',
    'version': '1.0.0',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/role_views.xml',
        'views/server_views.xml',
        'views/dish_views.xml',
        'views/table_views.xml',
        'views/order_views.xml',
        'views/discount_views.xml',
        'views/statistics_views.xml',
        'views/sync_wizard_views.xml',
        'wizard/report_wizard_views.xml',
        'views/menu_views.xml',
        'report/statistics_report_templates.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'external_dependencies': {
        'python': ['requests', 'matplotlib'],
    },
}