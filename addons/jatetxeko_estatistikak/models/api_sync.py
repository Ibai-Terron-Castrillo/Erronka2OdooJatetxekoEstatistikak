# -*- coding: utf-8 -*-
import requests
import json
import logging
import pytz
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timezone
import traceback

_logger = logging.getLogger(__name__)

# C# API Base URL (port 5093)
# Use host.docker.internal to connect to host machine from Docker container
API_BASE_URL = "http://host.docker.internal:5093/api"


class ApiSync(models.AbstractModel):
    _name = "jatetxeko.api.sync"
    _description = "API Sinkronizazioa"

    @api.model
    def _get_api_data(self, endpoint):
        """Generic method to fetch data from C# API"""
        try:
            url = f"{API_BASE_URL}/{endpoint}"
            _logger.info(f"Fetching API data from: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            _logger.info(f"API Response for {endpoint}: {len(data) if isinstance(data, list) else 1} records")
            return data
        except requests.RequestException as e:
            _logger.error(f"API Error fetching {endpoint}: {str(e)}")
            raise Exception(_("API errorea: %s") % str(e))

    @api.model
    def _parse_api_datetime(self, date_val):
        """
        Parse datetime from API and adjust for timezone offset to show same time in Odoo UI.
        Odoo stores in UTC and displays in user's timezone.
        To show "12:00" for a Madrid user (+2h), we store "10:00" in DB.
        """
        if not date_val:
            return False
            
        dt = False
        if isinstance(date_val, str):
            try:
                # Remove Z and fractional seconds
                clean = date_val.replace('Z', '').split('.')[0]
                dt = datetime.strptime(clean, '%Y-%m-%dT%H:%M:%S')
            except:
                return False
        elif isinstance(date_val, datetime):
            dt = date_val.replace(tzinfo=None)
        else:
            return False

        # Adjust for user timezone offset to bypass Odoo's display conversion
        # This makes the "Clock time" the same regardless of timezone
        user_tz_name = self.env.user.tz or 'Europe/Madrid'
        try:
            user_tz = pytz.timezone(user_tz_name)
            # Localize naive dt as if it was in user's timezone
            local_dt = user_tz.localize(dt, is_dst=None)
            # Convert to UTC
            utc_dt = local_dt.astimezone(pytz.utc)
            # Return naive UTC dt to save in Odoo
            return utc_dt.replace(tzinfo=None)
        except:
            return dt # Fallback to original naive if TZ fails

    @api.model
    def _create_sync_log(self, sync_type, status, records_synced=0, error_message=None):
        """Create sync log entry"""
        try:
            self.env['jatetxeko.sync.log'].create({
                'sync_type': sync_type,
                'status': status,
                'records_synced': records_synced,
                'error_message': error_message,
            })
        except Exception as e:
            _logger.error(f"Error creating sync log: {str(e)}")

    @api.model
    def sync_roles(self):
        """Sync rolak (roles) from C# API"""
        data = self._get_api_data("Rolak")
        Rola = self.env['jatetxeko.rola'].sudo()
        synced = 0

        for item in data:
            item_id = item.get('id')
            izena = item.get('izena')

            existing = Rola.search([('external_id', '=', item_id)], limit=1)
            vals = {
                'name': izena or f'Rola {item_id}',
                'external_id': item_id,
            }
            if existing:
                existing.write(vals)
            else:
                Rola.create(vals)
            synced += 1
        return synced

    @api.model
    def sync_servers(self):
        """Sync langileak (workers/servers) from C# API"""
        data = self._get_api_data("Langileak")
        Zerbitzaria = self.env['jatetxeko.zerbitzaria'].sudo()
        Rola = self.env['jatetxeko.rola'].sudo()
        synced = 0

        for item in data:
            item_id = item.get('id')
            izena = item.get('izena')
            erabiltzailea = item.get('erabiltzailea')
            pasahitza = item.get('pasahitza')
            aktibo = item.get('aktibo', 'Bai')
            rola_id_api = item.get('rolaId')
            txat_baimena = item.get('txatBaimena', False)
            erregistro_data = item.get('erregistroData')

            # Aktibo field is string "Bai" or "Ez"
            active = aktibo == 'Bai'

            # Find role by external_id
            rola = False
            if rola_id_api:
                rola = Rola.search([('external_id', '=', rola_id_api)], limit=1)

            # Parse registration date
            erregistro_data = self._parse_api_datetime(item.get('erregistroData'))

            existing = Zerbitzaria.search([('external_id', '=', item_id)], limit=1)
            vals = {
                'name': izena or 'Izenik gabe',
                'external_id': item_id,
                'active': active,
                'erabiltzailea': erabiltzailea,
                'pasahitza': pasahitza,
                'role_id': rola.id if rola else False,
                'txat_baimena': txat_baimena if isinstance(txat_baimena, bool) else False,
                'erregistro_data': erregistro_data,
            }
            if existing:
                existing.write(vals)
            else:
                Zerbitzaria.create(vals)
            synced += 1
        return synced

    @api.model
    def sync_dishes(self):
        """Sync platerak (dishes) from C# API"""
        data = self._get_api_data("Platerak")
        Platera = self.env['jatetxeko.platera'].sudo()
        synced = 0

        for item in data:
            item_id = item.get('id')
            izena = item.get('izena')
            prezioa = item.get('prezioa', 0.0)
            erabilgarri = item.get('erabilgarri', 'Bai')

            # Erabilgarri field is string "Bai" or "Ez"
            active = erabilgarri == 'Bai'

            existing = Platera.search([('external_id', '=', item_id)], limit=1)
            vals = {
                'name': izena or 'Izenik gabe',
                'external_id': item_id,
                'price': float(prezioa),
                'active': active,
            }
            if existing:
                existing.write(vals)
            else:
                Platera.create(vals)
            synced += 1
        return synced

    @api.model
    def sync_tables(self):
        """Sync mahiak (tables) from C# API"""
        data = self._get_api_data("Mahaiak")
        Mahia = self.env['jatetxeko.mahia'].sudo()
        synced = 0

        for item in data:
            item_id = item.get('id')
            mahaia_zbk = item.get('mahaiaZbk')
            edukiera = item.get('edukiera', 4)
            egoera = item.get('egoera')

            existing = Mahia.search([('external_id', '=', item_id)], limit=1)
            vals = {
                'name': str(mahaia_zbk or item_id),
                'external_id': item_id,
                'capacity': edukiera or 4,
                'active': True,  # egoera can be null, default to active
            }
            if existing:
                existing.write(vals)
            else:
                Mahia.create(vals)
            synced += 1
        return synced

    @api.model
    def sync_orders(self, date_from=None):
        """Sync zerbitzuak (services/orders) from C# API"""
        # Inportazio seguruak metodo barruan, erroreak saihesteko
        try:
            from dateutil import parser
        except ImportError:
            # dateutil ez badago, erabili datetime.strptime (ISO formatu simpleetarako)
            parser = None
            _logger.warning("dateutil not available, falling back to basic datetime parsing")

        endpoint = "Zerbitzuak"
        if date_from:
            endpoint += f"?from={date_from}"

        data = self._get_api_data(endpoint)
        Eskaera = self.env['jatetxeko.eskaera'].sudo()
        EskaeraLine = self.env['jatetxeko.eskaera.line'].sudo()
        synced = 0

        # Get order details (lines) from ZerbitzuXehetasunak
        details_data = self._get_api_data("ZerbitzuXehetasunak")
        _logger.info(f"=== SYNC ORDERS ===")
        _logger.info(f"Total details received: {len(details_data)}")

        # Group details by zerbitzuaId
        details_by_order = {}
        for detail in details_data:
            order_id = detail.get('zerbitzuaId')
            if order_id not in details_by_order:
                details_by_order[order_id] = []
            details_by_order[order_id].append(detail)

        for item in data:
            item_id = item.get('id')
            langile_id = item.get('langileId')
            mahaia_id = item.get('mahaiaId')
            guztira = item.get('guztira', 0.0)
            egoera = item.get('egoera')
            
            # Map relations
            server = self.env['jatetxeko.zerbitzaria'].sudo().search(
                [('external_id', '=', langile_id)], limit=1)
            table = self.env['jatetxeko.mahia'].sudo().search(
                [('external_id', '=', mahaia_id)], limit=1)

            order_date = self._parse_api_datetime(item.get('eskaeraData'))

            # Map status
            status_map = {
                'Itxaropean': 'draft',
                'Eskatuta': 'confirmed',
                'Egiten': 'confirmed',
                'Mahi_Gaineen': 'confirmed',
                'Ordainduta': 'paid',
            }
            state = status_map.get(egoera, 'draft')

            existing = Eskaera.search([('external_id', '=', item_id)], limit=1)
            vals = {
                'external_id': item_id,
                'name': f"ESK-{item_id:06d}",
                'date': order_date,
                'zerbitzaria_id': server.id if server else False,
                'mahia_id': table.id if table else False,
                'state': state,
            }

            if existing:
                existing.write(vals)
                order = existing
            else:
                order = Eskaera.create(vals)

            # Sync lines for this order
            order_details = details_by_order.get(item_id, [])
            _logger.info(f"Order {item_id} has {len(order_details)} lines in API")

            # Remove existing lines to re-import (simpler than matching)
            order.line_ids.unlink()

            for detail in order_details:
                platera_id = detail.get('plateraId')
                kantitatea = detail.get('kantitatea', 1)
                prezioa = detail.get('prezioUnitarioa', 0.0)

                dish = self.env['jatetxeko.platera'].sudo().search(
                    [('external_id', '=', platera_id)], limit=1)

                EskaeraLine.create({
                    'eskaera_id': order.id,
                    'platera_id': dish.id if dish else False,
                    'quantity': kantitatea,
                    'price_unit': float(prezioa),
                })

            # Force recompute totals for the order
            order._compute_totals()

            synced += 1
        return synced

    @api.model
    def sync_all(self):
        """Full sync from C# API"""
        try:
            roles = self.sync_roles()
            servers = self.sync_servers()
            dishes = self.sync_dishes()
            tables = self.sync_tables()
            orders = self.sync_orders()

            total_synced = roles + servers + dishes + tables + orders
            self._create_sync_log('full', 'success', total_synced)
            return {'status': 'success', 'records_synced': total_synced}

        except Exception as e:
            error_msg = str(e)
            _logger.error(f"Sync all error: {error_msg}\n{traceback.format_exc()}")
            self._create_sync_log('full', 'failed', 0, error_msg)
            return {'status': 'failed', 'error': error_msg}

    @api.model
    def sync_masters(self):
        """Sync master data (roles, servers, dishes, tables) only"""
        try:
            roles = self.sync_roles()
            servers = self.sync_servers()
            dishes = self.sync_dishes()
            tables = self.sync_tables()

            total_synced = roles + servers + dishes + tables
            self._create_sync_log('partial', 'success', total_synced)
            return {'status': 'success', 'records_synced': total_synced}

        except Exception as e:
            error_msg = str(e)
            _logger.error(f"Sync masters error: {error_msg}\n{traceback.format_exc()}")
            self._create_sync_log('partial', 'failed', 0, error_msg)
            return {'status': 'failed', 'error': error_msg}

    @api.model
    def push_worker_to_api(self, worker):
        """Push a worker from Odoo to C# API"""
        import requests

        # Get role external_id from Many2one
        rola_external_id = worker.role_id.external_id if worker.role_id else 2

        # Prepare data for API (matching Langileak model)
        payload = {
            'izena': worker.name,
            'erabiltzailea': worker.erabiltzailea,
            'pasahitza': worker.pasahitza,
            'aktibo': 'Bai' if worker.active else 'Ez',
            'rolaId': rola_external_id,
            'txatBaimena': worker.txat_baimena,
        }

        # If worker has external_id, update existing
        if worker.external_id:
            url = f"{API_BASE_URL}/Langileak/{worker.external_id}"
            try:
                response = requests.put(url, json=payload, timeout=30)
                response.raise_for_status()
                _logger.info(f"Updated worker {worker.name} in API (ID: {worker.external_id})")
                return {'status': 'updated', 'external_id': worker.external_id}
            except requests.RequestException as e:
                _logger.error(f"Error updating worker: {str(e)}")
                raise Exception(_("Errorea langilea eguneratzean: %s") % str(e))
        else:
            # Create new worker in API
            url = f"{API_BASE_URL}/Langileak"
            try:
                response = requests.post(url, json=payload, timeout=30)
                response.raise_for_status()
                # Get the new ID from response
                result = response.json()
                new_id = result.get('id')
                if new_id:
                    worker.write({'external_id': new_id})
                _logger.info(f"Created worker {worker.name} in API (ID: {new_id})")
                return {'status': 'created', 'external_id': new_id}
            except requests.RequestException as e:
                _logger.error(f"Error creating worker: {str(e)}")
                raise Exception(_("Errorea langilea sortzean: %s") % str(e))

    @api.model
    def push_all_workers_to_api(self):
        """Push all workers with username/password to C# API"""
        workers = self.env['jatetxeko.zerbitzaria'].search([
            ('erabiltzailea', '!=', False),
            ('pasahitza', '!=', False),
        ])
        pushed = 0
        errors = []

        for worker in workers:
            try:
                self.push_worker_to_api(worker)
                pushed += 1
            except Exception as e:
                errors.append(f"{worker.name}: {str(e)}")

        if errors:
            _logger.warning(f"Push workers errors: {errors}")

        return {
            'status': 'success' if not errors else 'partial',
            'pushed': pushed,
            'errors': errors,
        }