"""Start/check an isolated Django + real Celery -> Kubernetes Odoo API flow.

--setup creates only the explicitly named ecomparts-lab-integration project.
--verify creates LAB-E2E orders through authenticated HTTP, never through ORM.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
import struct
import subprocess
import time
import zlib

import requests

from benchmark_runner import kube, obj
from verify_odoo_lab import config

ROOT = Path(__file__).resolve().parents[1]
PROJECT = 'ecomparts-lab-integration'
ENV = ROOT / '.lab/marketplace-kubernetes.env'
COMPOSE = ['docker', 'compose', '--env-file', '.env.lab', '--env-file', str(ENV),
           '-p', PROJECT, '-f', 'docker-compose.yml', '-f', 'compose.lab.yml',
           '-f', 'compose.kubernetes.yml']


def command(args, timeout=600):
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True,
                            encoding='utf-8', errors='replace', timeout=timeout)
    if result.returncode:
        # Do not echo rendered Compose configuration or environment values.
        raise RuntimeError(result.stderr[-4000:] or 'Integration command failed')
    return result.stdout


def manage(*args):
    return command(COMPOSE + ['exec', '-T', 'backend', 'python', 'manage.py', *args])


def setup():
    base, odoo = config('.env.lab'), config('.env.k8s')
    networks = json.loads(command(['docker', 'inspect', 'ecomparts-k8s', '--format',
                                  '{{json .NetworkSettings.Networks}}']))
    if len(networks) != 1:
        raise RuntimeError('Expected a single private Docker network for Minikube')
    previous = config(str(ENV.relative_to(ROOT))) if ENV.exists() else {}
    values = {'LAB_MODE': '1', 'COMPOSE_PROJECT_NAME': PROJECT, 'DJANGO_PORT': '18001',
              'ODOO_URL': 'http://ecomparts-k8s:30069', 'ODOO_DB': odoo['ODOO_DB'],
              'ODOO_USERNAME': odoo['ODOO_SERVICE_LOGIN'],
              'ODOO_PASSWORD': odoo['ODOO_SERVICE_PASS'],
              'LAB_E2E_PASSWORD': previous.get('LAB_E2E_PASSWORD') or secrets.token_urlsafe(24),
              'LAB_E2E_ODOO_PASSWORD_PREFIX': odoo['ODOO_ADMIN_PASS'],
              'MINIKUBE_DOCKER_NETWORK': next(iter(networks))}
    if base.get('DJANGO_DEBUG', '').lower() not in ('1', 'true'):
        raise RuntimeError('Requires a DEBUG lab, never production')
    ENV.parent.mkdir(exist_ok=True)
    ENV.write_text(''.join(f'{key}={value}\n' for key, value in values.items()), encoding='utf-8')
    if any(job['metadata']['name'].startswith('bench-') and job['status'].get('active', 0)
           for job in obj('get', 'jobs', '-o', 'json')['items']):
        raise RuntimeError('Finish benchmark jobs before integration setup')
    kube('apply', '-f', str(ROOT / 'k8s/odoo/marketplace-service.yaml'))
    print('Building the isolated backend and worker...', flush=True)
    command(COMPOSE + ['build', 'backend', 'celery_worker'], timeout=1800)
    print('Starting the isolated PostgreSQL and Redis...', flush=True)
    command(COMPOSE + ['up', '-d', '--wait', 'postgres', 'redis'])
    print('Starting Django and a real Celery worker...', flush=True)
    command(COMPOSE + ['up', '-d', '--no-deps', '--wait', '--wait-timeout', '240',
                       'backend', 'celery_worker'])
    print('Integration API ready: http://127.0.0.1:18001', flush=True)


def png():
    def chunk(name, data):
        return struct.pack('!I', len(data)) + name + data + struct.pack('!I', zlib.crc32(name + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', 1, 1, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\x00\x00\x80\xff')) + chunk(b'IEND', b''))


def verify():
    values = config(str(ENV.relative_to(ROOT)))
    public = {'at_utc': datetime.now(timezone.utc).isoformat(), 'project': PROJECT,
              'api_url': 'http://127.0.0.1:18001', 'odoo_url': values['ODOO_URL'],
              'scope': 'authenticated HTTP API; real Celery worker; draft sale in correct company',
              'celery_eager': False, 'valid': False, 'cases': []}
    output = ROOT / '.lab/integration-result.json'
    if output.exists():
        previous = json.loads(output.read_text(encoding='utf-8'))
        archive = ROOT / '.lab' / ('integration-attempt-' + previous['at_utc'].replace(':', '').replace('.', '') + '.json')
        archive.write_text(json.dumps(previous, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    def save():
        output.write_text(json.dumps(public, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    save()
    try:
        fixture_output = manage('prepare_integration_lab', '--fresh-customer')
        line = next(line for line in fixture_output.splitlines() if line.startswith('LAB_FIXTURE_JSON:'))
        fixtures = json.loads(line.split(':', 1)[1])
        session = requests.Session()
        session.trust_env = False
        base = public['api_url'] + '/api/v1/'
        response = session.post(base + 'auth/token/', json={
            'username': fixtures['username'], 'password': values['LAB_E2E_PASSWORD']}, timeout=30)
        response.raise_for_status()
        session.headers['Authorization'] = 'Bearer ' + response.json()['access']
        for case in fixtures['cases']:
            result = {**case}
            public['cases'].append(result)
            response = session.post(base + 'orders/orders/create_order/', json={
                'customer_id': fixtures['customer_id'], 'delivery_method': 'tienda',
                'customer_notes': 'LAB-E2E API Kubernetes ' + case['company'],
                'items': [{'product_id': case['product_id'], 'quantity': 1}]}, timeout=60)
            result['order_http_status'] = response.status_code
            if response.status_code != 201:
                raise RuntimeError('Order API failed: ' + response.text[:1500])
            order = response.json()
            # The endpoint returns the serialized order directly.
            if 'order' in order and isinstance(order['order'], dict):
                order = order['order']
            sub = order['sub_orders'][0]
            result.update({'order_id': order['id'], 'sub_order_number': sub['sub_order_number']})
            response = session.post(base + 'orders/orders/upload_payment_proof/', data={
                'sub_order_id': str(sub['id']), 'payment_method': 'transferencia',
                'operation_number': 'LAB-E2E-' + secrets.token_hex(6), 'amount': sub['total']},
                files={'file': ('LAB-E2E.png', png(), 'image/png')}, timeout=60)
            result['payment_proof_http_status'] = response.status_code
            if response.status_code != 201:
                raise RuntimeError('Payment proof API failed: ' + response.text[:1500])
            save()
        for result in public['cases']:
            text = manage('verify_marketplace_order', result['sub_order_number'], '--wait-seconds', '90')
            result['verification'] = next(line for line in text.splitlines() if line.startswith('OK SubOrder'))
            save()
        logs = command(COMPOSE + ['logs', '--no-color', '--since', public['at_utc'], 'celery_worker'])
        numbers = [case['sub_order_number'] for case in public['cases']]
        public['worker_container'] = PROJECT + '-celery-worker'
        public['worker_task_evidence'] = [line for line in logs.splitlines()
                                         if 'Sale Order creada en Odoo:' in line
                                         and any(number in line for number in numbers)]
        if any(not any(number in line for line in public['worker_task_evidence']) for number in numbers):
            raise RuntimeError('Missing correlated sale creation logs in the real Celery worker')
        public['valid'] = True
        print('OK: three HTTP orders A/B/C reached the correct Odoo companies through real Celery')
    except Exception as error:
        public['error_type'] = type(error).__name__
        raise
    finally:
        save()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--setup', action='store_true')
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--stop', action='store_true', help='Stop only the isolated integration containers, preserve volumes')
    args = parser.parse_args()
    if args.stop:
        if args.setup or args.verify:
            parser.error('--stop cannot be combined with setup or verification')
        command(COMPOSE + ['stop', 'backend', 'celery_worker', 'postgres', 'redis'])
        print('Isolated integration containers stopped; volumes preserved')
    elif not args.setup and not args.verify:
        parser.error('Choose --setup, --verify or --stop')
    if args.setup:
        setup()
    if args.verify:
        verify()
