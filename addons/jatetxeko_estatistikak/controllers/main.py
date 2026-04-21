# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class JatetxekoController(http.Controller):
    """
    REST API Controller for TPV integration
    """

    @http.route('/api/discount/validate', type='http', auth='public', methods=['POST'], csrf=False)
    def validate_discount(self, **kwargs):
        """
        API endpoint for TPV to validate discount codes

        Request:
            POST /api/discount/validate
            Content-Type: application/json
            Body: {"code": "ABC12345"}

        Response:
            {"valid": true, "percentage": 10} | {"valid": false, "message": "..."}
        """
        try:
            # Parse JSON body
            body = json.loads(request.httprequest.data.decode('utf-8'))
            code = body.get('code')

            if not code:
                return Response(
                    json.dumps({'valid': False, 'message': 'Kodea beharrezkoa da'}),
                    content_type='application/json',
                    status=400
                )

            # Validate the code
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
            _logger.error(f"Error validating discount: {str(e)}")
            return Response(
                json.dumps({'valid': False, 'message': str(e)}),
                content_type='application/json',
                status=500
            )

    @http.route('/api/discount/apply', type='http', auth='public', methods=['POST'], csrf=False)
    def apply_discount(self, **kwargs):
        """
        API endpoint to apply discount to an order

        Request:
            POST /api/discount/apply
            Content-Type: application/json
            Body: {"code": "ABC12345", "order_id": 123}

        Response:
            {"valid": true, "percentage": 10}
        """
        try:
            # Parse JSON body
            body = json.loads(request.httprequest.data.decode('utf-8'))
            code = body.get('code')
            order_id = body.get('order_id')

            if not code:
                return Response(
                    json.dumps({'valid': False, 'message': 'Kodea beharrezkoa da'}),
                    content_type='application/json',
                    status=400
                )

            # Validate the code
            discount_model = request.env['jatetxeko.deskontuak']
            result = discount_model.sudo().validate_code(code)

            if not result.get('valid'):
                return Response(
                    json.dumps(result),
                    content_type='application/json',
                    status=400
                )

            # Mark discount as used
            discount = request.env['jatetxeko.deskontuak'].sudo().browse(result['code_id'])
            discount.use_code()

            # Optionally link to order if order_id provided
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
            _logger.error(f"Error applying discount: {str(e)}")
            return Response(
                json.dumps({'valid': False, 'message': str(e)}),
                content_type='application/json',
                status=500
            )

    @http.route('/api/discount/list', type='http', auth='user', methods=['GET'], csrf=False)
    def list_discounts(self, **kwargs):
        """
        API endpoint to list all active discount codes (for admin)

        Request:
            GET /api/discount/list
            Authorization: session cookie

        Response:
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
            _logger.error(f"Error listing discounts: {str(e)}")
            return Response(
                json.dumps({'error': str(e)}),
                content_type='application/json',
                status=500
            )

    @http.route('/api/sync/status', type='http', auth='user', methods=['GET'], csrf=False)
    def sync_status(self, **kwargs):
        """
        API endpoint to check sync status

        Request:
            GET /api/sync/status

        Response:
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
            _logger.error(f"Error getting sync status: {str(e)}")
            return Response(
                json.dumps({'error': str(e)}),
                content_type='application/json',
                status=500
            )