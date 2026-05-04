# -*- coding: utf-8 -*-
import json
import logging
import unicodedata
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class JatetxekoController(http.Controller):
    """
    TPV integraziorako REST API kontrolatzailea
    REST API controller used by the TPV application.
    """

    @http.route('/api/discount/ping', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def discount_ping(self, **kwargs):
        """
        Simple endpoint to verify that the Odoo module routes are loaded.
        """
        return self._json_response({
            'status': 'ok',
            'message': 'Jatetxeko deskontuen API-a martxan dago'
        })

    @http.route([
        '/api/discount/validate',
        '/api/deskontuak/validate',
        '/api/deskontuak/balidatu',
    ], type='http', auth='public', methods=['POST'], csrf=False, cors='*')
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
            code = self._extract_code(body)

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

    @http.route([
        '/api/discount/apply',
        '/api/deskontuak/apply',
        '/api/deskontuak/aplikatu',
    ], type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def apply_discount(self, **kwargs):
        """
        Validate and mark a discount code as used from the TPV.

        Request body:
            {"code": "ABC12345", "order_id": 123}

        order_id is the external C# API service/order id. If an Odoo order exists
        with external_id == order_id, the discount is linked to that Odoo order.
        """
        try:
            body = self._read_json_body()
            code = self._normalize_code(self._extract_code(body))
            order_id = body.get('order_id')

            if not code:
                return self._json_response({
                    'valid': False,
                    'message': 'Kodea beharrezkoa da'
                }, status=200)

            discount_model = request.env['jatetxeko.deskontuak'].sudo()
            result = discount_model.validate_code(code)

            if not result.get('valid'):
                return self._json_response(result, status=200)

            discount = discount_model.browse(result['code_id'])

            if not discount.exists():
                return self._json_response({
                    'valid': False,
                    'message': 'Deskuntu kodea ez da existitzen'
                }, status=200)

            discount.use_code()

            linked_order_id = False
            if order_id:
                linked_order_id = self._link_discount_to_order(order_id, discount.id)

            return self._json_response({
                'valid': True,
                'percentage': result['percentage'],
                'code_id': discount.id,
                'linked_order_id': linked_order_id
            }, status=200)

        except ValueError as e:
            return self._json_response({
                'valid': False,
                'message': str(e)
            }, status=200)
        except Exception as e:
            _logger.exception('Error applying discount')
            return self._json_response({
                'valid': False,
                'message': str(e)
            }, status=500)

    @http.route('/api/discount/list', type='http', auth='user', methods=['GET'], csrf=False, cors='*')
    def list_discounts(self, **kwargs):
        """
        Deskuntu-kode aktibo guztiak zerrendatzeko API amaiera-puntua (adminentzat)

        Eskaera:
            GET /api/discount/list
            Authorization: session cookie

        Erantzuna:
            [{"id": 1, "code": "ABC12345", "percentage": 10, "active": true}, ...]
        List all discount codes for authenticated Odoo users.
        """
        try:
            discounts = request.env['jatetxeko.deskontuak'].sudo().search([])
            result = [{
                'id': d.id,
                'code': d.name,
                'percentage': d.percentage,
                'active': d.active,
                'usage_count': d.usage_count,
                'usage_limit': d.usage_limit,
                'valid_from': d.valid_from.isoformat() if d.valid_from else None,
                'valid_until': d.valid_until.isoformat() if d.valid_until else None,
            } for d in discounts]

            return self._json_response(result, status=200)

        except Exception as e:
            _logger.exception('Error listing discounts')
            return self._json_response({'error': str(e)}, status=500)

    @http.route('/api/sync/status', type='http', auth='user', methods=['GET'], csrf=False, cors='*')
    def sync_status(self, **kwargs):
        """
        Sinkronizazio egoera egiaztatzeko API amaiera-puntua

        Eskaera:
            GET /api/sync/status

        Erantzuna:
            {"last_sync": "2026-03-30 10:00:00", "status": "success", "records": 100}
        Check the last synchronization status.
        """
        try:
            last_log = request.env['jatetxeko.sync.log'].sudo().search(
                [], order='create_date desc', limit=1
            )

            if not last_log:
                return self._json_response({
                    'status': 'no_sync',
                    'message': 'Ez da sinkronizaziorik aurkitu'
                }, status=200)

            result = {
                'last_sync': last_log.create_date.isoformat() if last_log.create_date else None,
                'status': last_log.status,
                'sync_type': last_log.sync_type,
                'records_synced': last_log.records_synced,
                'error_message': last_log.error_message,
            }

            return self._json_response(result, status=200)

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
            _logger.exception('Error getting busiest day of month')
            return self._json_response({'error': str(e)}, status=500)

    def _read_json_body(self):
        raw_body = request.httprequest.get_data(as_text=True) or ''

        if not raw_body.strip():
            return {}

        try:
            return json.loads(raw_body)
        except json.JSONDecodeError:
            raise ValueError('JSON formatu baliogabea')

    def _normalize_code(self, code):
        if code is None:
            return ''

        normalized = unicodedata.normalize('NFKC', str(code))
        return ''.join(
            character
            for character in normalized
            if not character.isspace()
            and unicodedata.category(character) not in ('Cc', 'Cf')
        ).upper()

    def _extract_code(self, data):
        if not isinstance(data, dict):
            return ''

        for key in ('code', 'kodea', 'codigo', 'coupon_code', 'discount_code', 'name'):
            value = data.get(key)
            if value:
                return value

        return ''

    def _link_discount_to_order(self, order_id, discount_id):
        try:
            external_id = int(order_id)
        except (TypeError, ValueError):
            _logger.warning('Invalid order_id received from TPV: %s', order_id)
            return False

        order = request.env['jatetxeko.eskaera'].sudo().search(
            [('external_id', '=', external_id)], limit=1
        )

        if not order:
            _logger.warning(
                'No Odoo order found with external_id=%s. Discount usage was still registered.',
                external_id
            )
            return False

        order.write({'discount_id': discount_id})
        return order.id

    def _json_response(self, data, status=200):
        return Response(
            json.dumps(data, ensure_ascii=False),
            content_type='application/json; charset=utf-8',
            status=status
        )
