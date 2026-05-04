# -*- coding: utf-8 -*-
import os
import requests
import logging
import pytz
from urllib.parse import urlparse, urlunparse
from odoo import models, api, _
from datetime import datetime
import traceback

_logger = logging.getLogger(__name__)

# C# APIaren oinarrizko URLa (5093 portua)
# Docker edukiontzitik host makinara konektatzeko, host.docker.internal erabili
API_BASE_URL = "http://host.docker.internal:5093/api"
DEFAULT_API_BASE_URL = os.getenv("JATETXEKO_API_BASE_URL", API_BASE_URL)
DEFAULT_API_TIMEOUT = int(os.getenv("JATETXEKO_API_TIMEOUT", "30"))
DEFAULT_API_VERIFY_SSL = os.getenv("JATETXEKO_API_VERIFY_SSL", "false").strip().lower() in (
    "1", "true", "yes", "on"
)


class ApiSinkronizazioa(models.AbstractModel):
    _name = "jatetxeko.api.sync"
    _description = "API Sinkronizazioa"

    @api.model
    def _to_bool(self, value, default=False):
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        return str(value).strip().lower() in ("1", "true", "yes", "on", "bai")

    @api.model
    def _normalize_base_url(self, url):
        url = (url or DEFAULT_API_BASE_URL).strip()
        return url.rstrip('/')

    @api.model
    def _get_api_config(self):
        params = self.env['ir.config_parameter'].sudo()

        base_url = self._normalize_base_url(
            params.get_param('jatetxeko.api.base_url', DEFAULT_API_BASE_URL)
        )
        verify_ssl = self._to_bool(
            params.get_param('jatetxeko.api.verify_ssl', DEFAULT_API_VERIFY_SSL),
            default=DEFAULT_API_VERIFY_SSL,
        )

        timeout_raw = params.get_param('jatetxeko.api.timeout', DEFAULT_API_TIMEOUT)
        try:
            timeout = int(timeout_raw)
        except (TypeError, ValueError):
            timeout = DEFAULT_API_TIMEOUT

        return {
            'base_url': base_url,
            'verify_ssl': verify_ssl,
            'timeout': timeout,
        }

    @api.model
    def _is_local_dev_host(self, hostname):
        return hostname in ('host.docker.internal', 'localhost', '127.0.0.1')

    @api.model
    def _build_candidate_urls(self, endpoint, base_url=None):
        config = self._get_api_config()
        api_base = self._normalize_base_url(base_url or config['base_url'])
        endpoint = (endpoint or '').lstrip('/')
        candidates = [f"{api_base}/{endpoint}"]

        parsed = urlparse(api_base)
        if parsed.scheme == 'https' and self._is_local_dev_host(parsed.hostname):
            netloc = parsed.netloc
            if parsed.port == 7236:
                netloc = parsed.netloc.replace(':7236', ':5093')
            elif ':' not in parsed.netloc:
                netloc = f"{parsed.hostname}:5093"

            http_base = urlunparse((
                'http',
                netloc,
                parsed.path,
                '',
                '',
                '',
            )).rstrip('/')
            fallback_url = f"{http_base}/{endpoint}"
            if fallback_url not in candidates:
                candidates.append(fallback_url)

        return candidates

    @api.model
    def _request_api(self, method, endpoint, payload=None):
        config = self._get_api_config()
        urls = self._build_candidate_urls(endpoint, config['base_url'])
        errors = []

        for url in urls:
            verify_ssl = config['verify_ssl']
            try:
                _logger.info(
                    "API request %s %s (verify_ssl=%s, timeout=%s)",
                    method.upper(), url, verify_ssl, config['timeout']
                )
                response = requests.request(
                    method=method,
                    url=url,
                    json=payload,
                    timeout=config['timeout'],
                    verify=verify_ssl,
                )
                response.raise_for_status()
                return response

            except requests.exceptions.SSLError as e:
                errors.append(f"{url}: {str(e)}")
                parsed = urlparse(url)
                if parsed.scheme == 'https' and self._is_local_dev_host(parsed.hostname):
                    try:
                        _logger.warning(
                            "SSL verify failed against %s. Retrying once with verify=False because it is a local development host.",
                            url,
                        )
                        response = requests.request(
                            method=method,
                            url=url,
                            json=payload,
                            timeout=config['timeout'],
                            verify=False,
                        )
                        response.raise_for_status()
                        return response
                    except requests.RequestException as retry_error:
                        errors.append(f"{url} (retry verify=False): {str(retry_error)}")
                        continue

            except requests.RequestException as e:
                errors.append(f"{url}: {str(e)}")
                continue

        raise Exception(_("API errorea: %s") % " | ".join(errors))

    @api.model
    def _get_api_data(self, endpoint):
        """C# API-tik datuak eskuratzeko metodo generikoa"""
        response = self._request_api('get', endpoint)
        data = response.json()
        _logger.info(
            "API Response for %s: %s records",
            endpoint,
            len(data) if isinstance(data, list) else 1,
        )
        return data

    @api.model
    def _parse_api_datetime(self, date_val):
        """
        API-tik datorren datetime-a parseatu eta ordu-zonaren offset-a doitu, Odoo UI-n ordu bera ikusteko.
        Odoo-k UTC-n gordetzen du eta erabiltzailearen ordu-zonan erakusten du.
        Madrilgo erabiltzaile batek (+2h) "12:00" ikus dezan, DB-n "10:00" gordetzen dugu.
        """
        if not date_val:
            return False

        dt = False
        if isinstance(date_val, str):
            try:
                clean = date_val.replace('Z', '').split('.')[0]
                dt = datetime.strptime(clean, '%Y-%m-%dT%H:%M:%S')
            except Exception:
                return False
        elif isinstance(date_val, datetime):
            dt = date_val.replace(tzinfo=None)
        else:
            return False

        # Erabiltzailearen TZ offset-a doitu, Odoo-ren bistaratze-konbertsioa saihesteko
        # Horrela "orduko" balioa berdina da ordu-zona edozein dela ere
        user_tz_name = self.env.user.tz or 'Europe/Madrid'
        try:
            user_tz = pytz.timezone(user_tz_name)
            # dt naive-a erabiltzailearen ordu-zonan dagoela suposatuta lokalizatu
            local_dt = user_tz.localize(dt, is_dst=None)
            # UTC-ra bihurtu
            utc_dt = local_dt.astimezone(pytz.utc)
            # UTC naive-a itzuli Odoo-n gordetzeko
            return utc_dt.replace(tzinfo=None)
        except Exception:
            return dt

    @api.model
    def _create_sync_log(self, sync_type, status, records_synced=0, error_message=None):
        """Sinkronizazio log sarrera sortu"""
        try:
            self.env['jatetxeko.sync.log'].create({
                'sync_type': sync_type,
                'status': status,
                'records_synced': records_synced,
                'error_message': error_message,
            })
        except Exception as e:
            _logger.error(f"Sinkronizazio log-a sortzean errorea: {str(e)}")

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

            active = aktibo == 'Bai'

            rola = False
            if rola_id_api:
                rola = Rola.search([('external_id', '=', rola_id_api)], limit=1)

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

            existing = Mahia.search([('external_id', '=', item_id)], limit=1)
            vals = {
                'name': str(mahaia_zbk or item_id),
                'external_id': item_id,
                'capacity': edukiera or 4,
                'active': True,
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
        try:
            from dateutil import parser  # noqa: F401
        except ImportError:
            _logger.warning("dateutil not available, falling back to basic datetime parsing")

        endpoint = "Zerbitzuak"
        if date_from:
            endpoint += f"?from={date_from}"

        data = self._get_api_data(endpoint)
        Eskaera = self.env['jatetxeko.eskaera'].sudo()
        EskaeraLine = self.env['jatetxeko.eskaera.line'].sudo()
        synced = 0

        details_data = self._get_api_data("ZerbitzuXehetasunak")
        _logger.info(f"=== SYNC ORDERS ===")
        _logger.info(f"Total details received: {len(details_data)}")

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
            egoera = item.get('egoera')

            server = self.env['jatetxeko.zerbitzaria'].sudo().search(
                [('external_id', '=', langile_id)], limit=1)
            table = self.env['jatetxeko.mahia'].sudo().search(
                [('external_id', '=', mahaia_id)], limit=1)

            order_date = self._parse_api_datetime(item.get('eskaeraData'))

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

            # Eskaera honetako lerroak sinkronizatu
            order_details = details_by_order.get(item_id, [])
            _logger.info(f"Eskaera {item_id}: API-n {len(order_details)} lerro daude")

            # Existitzen diren lerroak ezabatu berriro inportatzeko (parekatzea baino errazagoa)
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

            # Eskaeraren guztizkoak berriro kalkulatzera behartu
            order._compute_totals()
            synced += 1
        return synced

    @api.model
    def sync_all(self):
        """Sinkronizazio osoa C# API-tik"""
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
            _logger.error(f"Sinkronizazio osoaren errorea: {error_msg}\n{traceback.format_exc()}")
            self._create_sync_log('full', 'failed', 0, error_msg)
            return {'status': 'failed', 'error': error_msg}

    @api.model
    def sync_masters(self):
        """Datu maisuak soilik sinkronizatu (rolak, zerbitzariak, platerak, mahiak)"""
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
            _logger.error(f"Datu maisuen sinkronizazio errorea: {error_msg}\n{traceback.format_exc()}")
            self._create_sync_log('partial', 'failed', 0, error_msg)
            return {'status': 'failed', 'error': error_msg}

    @api.model
    def push_worker_to_api(self, worker):
        """Odootik C# APIra langile bat bidali"""
        rola_external_id = worker.role_id.external_id if worker.role_id else 2

        payload = {
            'izena': worker.name,
            'erabiltzailea': worker.erabiltzailea,
            'pasahitza': worker.pasahitza,
            'aktibo': 'Bai' if worker.active else 'Ez',
            'rolaId': rola_external_id,
            'txatBaimena': worker.txat_baimena,
        }

        if worker.external_id:
            endpoint = f"Langileak/{worker.external_id}"
            try:
                self._request_api('put', endpoint, payload)
                _logger.info(f"Langilea eguneratuta API-n: {worker.name} (ID: {worker.external_id})")
                return {'status': 'updated', 'external_id': worker.external_id}
            except Exception as e:
                _logger.error(f"Langilea eguneratzean errorea: {str(e)}")
                raise Exception(_("Errorea langilea eguneratzean: %s") % str(e))

        try:
            response = self._request_api('post', "Langileak", payload)
            result = response.json()
            new_id = result.get('id') or result.get('Id')
            if new_id:
                worker.write({'external_id': new_id})
            _logger.info(f"Langilea sortuta API-n: {worker.name} (ID: {new_id})")
            return {'status': 'created', 'external_id': new_id}
        except Exception as e:
            _logger.error(f"Langilea sortzean errorea: {str(e)}")
            raise Exception(_("Errorea langilea sortzean: %s") % str(e))

    @api.model
    def push_all_workers_to_api(self):
        """Erabiltzailea/pasahitza duten langile guztiak C# APIra bidali"""
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
            _logger.warning(f"Langileak bidaltzean erroreak: {errors}")

        return {
            'status': 'success' if not errors else 'partial',
            'pushed': pushed,
            'errors': errors,
        }
