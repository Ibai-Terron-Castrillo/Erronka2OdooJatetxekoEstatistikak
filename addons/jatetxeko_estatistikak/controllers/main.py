# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class JatetxekoController(http.Controller):
    """
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
        Validate a discount code from the TPV.

        Request body:
            {"code": "ABC12345"}

        Response:
            {"valid": true, "percentage": 10.0, "code_id": 1}
            {"valid": false, "message": "..."}
        """
        try:
            body = self._read_json_body()
            code = self._normalize_code(body.get('code'))

            if not code:
                return self._json_response({
                    'valid': False,
                    'message': 'Kodea beharrezkoa da'
                }, status=200)

            result = request.env['jatetxeko.deskontuak'].sudo().validate_code(code)
            return self._json_response(result, status=200)

        except ValueError as e:
            return self._json_response({
                'valid': False,
                'message': str(e)
            }, status=200)
        except Exception as e:
            _logger.exception('Error validating discount')
            return self._json_response({
                'valid': False,
                'message': str(e)
            }, status=500)

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
            code = self._normalize_code(body.get('code'))
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
            _logger.exception('Error getting sync status')
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

        return str(code).strip().upper()

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
