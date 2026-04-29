# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class JatetxekoController(http.Controller):
    """
    TPV integraziorako REST API kontrolatzailea
    """

    @http.route('/api/discount/validate', type='http', auth='public', methods=['POST'], csrf=False)
    def validate_discount(self, **kwargs):
        """
        TPVk deskontu-kodeak balioztatzeko API amaiera-puntua

        Eskaera:
            POST /api/discount/validate
            Content-Type: application/json
            Body: {"code": "ABC12345"}

        Erantzuna:
            {"valid": true, "percentage": 10} | {"valid": false, "message": "..."}
        """
        try:
            # JSON gorputza parseatu
            body = json.loads(request.httprequest.data.decode('utf-8'))
            code = body.get('code')

            if not code:
                return Response(
                    json.dumps({'valid': False, 'message': 'Kodea beharrezkoa da'}),
                    content_type='application/json',
                    status=400
                )

            # Kodea balioztatu
            discount_model = request.env['jatetxeko.deskontuak']
            result = discount_model.sudo().validate_code(code)

            return Response(
                json.dumps(result),
                content_type='application/json',
                status=200 if result.get('valid') else 400
            )

        except json.JSONDecodeError:
            return Response(
                json.dumps({'valid': False, 'message': 'JSON formatu baliogabea'}),
                content_type='application/json',
                status=400
            )
        except Exception as e:
            _logger.error(f"Deskuntua balioztatzean errorea: {str(e)}")
            return Response(
                json.dumps({'valid': False, 'message': str(e)}),
                content_type='application/json',
                status=500
            )

    @http.route('/api/discount/apply', type='http', auth='public', methods=['POST'], csrf=False)
    def apply_discount(self, **kwargs):
        """
        Eskaera bati deskontua aplikatzeko API amaiera-puntua

        Eskaera:
            POST /api/discount/apply
            Content-Type: application/json
            Body: {"code": "ABC12345", "order_id": 123}

        Erantzuna:
            {"valid": true, "percentage": 10}
        """
        try:
            # JSON gorputza parseatu
            body = json.loads(request.httprequest.data.decode('utf-8'))
            code = body.get('code')
            order_id = body.get('order_id')

            if not code:
                return Response(
                    json.dumps({'valid': False, 'message': 'Kodea beharrezkoa da'}),
                    content_type='application/json',
                    status=400
                )

            # Kodea balioztatu
            discount_model = request.env['jatetxeko.deskontuak']
            result = discount_model.sudo().validate_code(code)

            if not result.get('valid'):
                return Response(
                    json.dumps(result),
                    content_type='application/json',
                    status=400
                )

            # Deskuntua erabilita bezala markatu
            discount = request.env['jatetxeko.deskontuak'].sudo().browse(result['code_id'])
            discount.use_code()

            # order_id emanda badago, aukeran eskaerari lotu
            if order_id:
                order = request.env['jatetxeko.eskaera'].sudo().browse(order_id)
                if order.exists():
                    order.write({'discount_id': discount.id})

            return Response(
                json.dumps({
                    'valid': True,
                    'percentage': result['percentage'],
                    'code_id': discount.id
                }),
                content_type='application/json',
                status=200
            )

        except json.JSONDecodeError:
            return Response(
                json.dumps({'valid': False, 'message': 'JSON formatu baliogabea'}),
                content_type='application/json',
                status=400
            )
        except Exception as e:
            _logger.error(f"Deskuntua aplikatzean errorea: {str(e)}")
            return Response(
                json.dumps({'valid': False, 'message': str(e)}),
                content_type='application/json',
                status=500
            )

    @http.route('/api/discount/list', type='http', auth='user', methods=['GET'], csrf=False)
    def list_discounts(self, **kwargs):
        """
        Deskuntu-kode aktibo guztiak zerrendatzeko API amaiera-puntua (adminentzat)

        Eskaera:
            GET /api/discount/list
            Authorization: session cookie

        Erantzuna:
            [{"id": 1, "code": "ABC12345", "percentage": 10, "active": true}, ...]
        """
        try:
            discounts = request.env['jatetxeko.deskontuak'].search([])
            result = [{
                'id': d.id,
                'code': d.name,
                'percentage': d.percentage,
                'active': d.active,
                'usage_count': d.usage_count,
                'usage_limit': d.usage_limit,
            } for d in discounts]

            return Response(
                json.dumps(result),
                content_type='application/json',
                status=200
            )

        except Exception as e:
            _logger.error(f"Deskuntuak zerrendatzean errorea: {str(e)}")
            return Response(
                json.dumps({'error': str(e)}),
                content_type='application/json',
                status=500
            )

    @http.route('/api/sync/status', type='http', auth='user', methods=['GET'], csrf=False)
    def sync_status(self, **kwargs):
        """
        Sinkronizazio egoera egiaztatzeko API amaiera-puntua

        Eskaera:
            GET /api/sync/status

        Erantzuna:
            {"last_sync": "2026-03-30 10:00:00", "status": "success", "records": 100}
        """
        try:
            last_log = request.env['jatetxeko.sync.log'].search([], order='create_date desc', limit=1)

            if not last_log:
                return Response(
                    json.dumps({'status': 'no_sync', 'message': 'Ez da sinkronizaziorik aurkitu'}),
                    content_type='application/json',
                    status=200
                )

            result = {
                'last_sync': last_log.create_date.isoformat() if last_log.create_date else None,
                'status': last_log.status,
                'sync_type': last_log.sync_type,
                'records_synced': last_log.records_synced,
                'error_message': last_log.error_message,
            }

            return Response(
                json.dumps(result),
                content_type='application/json',
                status=200
            )

        except Exception as e:
            _logger.error(f"Sinkronizazio egoera lortzean errorea: {str(e)}")
            return Response(
                json.dumps({'error': str(e)}),
                content_type='application/json',
                status=500
            )

    @http.route('/api/stats/busiest_day_of_month', type='http', auth='user', methods=['GET'], csrf=False)
    def busiest_day_of_month(self, **kwargs):
        try:
            year_param = request.params.get('year')
            year = int(year_param) if year_param else None
            result = request.env['jatetxeko.eskaera'].sudo().get_busiest_day_of_month(year=year)
            return Response(
                json.dumps(result),
                content_type='application/json',
                status=200
            )
        except ValueError:
            return Response(
                json.dumps({'error': 'year parametroa zenbaki bat izan behar da'}),
                content_type='application/json',
                status=400
            )
        except Exception as e:
            _logger.error(f"Hilabeteko egun jendetsuena kalkulatzean errorea: {str(e)}")
            return Response(
                json.dumps({'error': str(e)}),
                content_type='application/json',
                status=500
            )
