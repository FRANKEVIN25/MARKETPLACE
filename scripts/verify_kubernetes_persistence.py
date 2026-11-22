"""Comprueba un registro PostgreSQL y un archivo del filestore tras recrear Pods."""

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import re
import time
from urllib.error import URLError
import uuid

from verify_odoo_lab import Odoo, ROOT, RpcError, config, require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action', choices=['create', 'check'], required=True)
    parser.add_argument('--profile', default='ecomparts-k8s')
    parser.add_argument('--base-url', default='http://127.0.0.1:18070')
    parser.add_argument('--stage', default='after_recreation')
    args = parser.parse_args()
    require(re.fullmatch(r'ecomparts-k8s(?:-[a-z0-9-]+)?', args.profile), 'Perfil de laboratorio no valido')
    values = config('.env.k8s')
    state_path = ROOT / '.lab' / f'{args.profile}-persistence.json'
    for attempt in range(5):
        try:
            rpc = Odoo(args.base_url, values['ODOO_DB'], values['ODOO_ADMIN_LOGIN'], values['ODOO_ADMIN_PASS'])
            break
        except (RpcError, URLError):
            if attempt == 4:
                raise
            time.sleep(2)

    if args.action == 'create':
        marker = 'LAB-K8S-' + uuid.uuid4().hex
        content = ('ECOMPARTS bloque 2: persistencia de registro y adjunto ' + marker).encode()
        partner_id = rpc.execute('res.partner', 'create', [{'name': marker}])
        attachment_id = rpc.execute('ir.attachment', 'create', [{
            'name': marker + '.txt', 'type': 'binary',
            'datas': base64.b64encode(content).decode(),
            'res_model': 'res.partner', 'res_id': partner_id,
            'mimetype': 'text/plain',
        }])
        attachment = rpc.execute('ir.attachment', 'read', [[attachment_id]], fields=['store_fname'])[0]
        require(bool(attachment['store_fname']), 'El adjunto no se guardo en el filestore')
        state = {
            'profile': args.profile, 'marker': marker, 'partner_id': partner_id,
            'attachment_id': attachment_id, 'content_sha256': hashlib.sha256(content).hexdigest(),
            'stored_in_filestore': True, 'checks': [],
        }
    else:
        state = json.loads(state_path.read_text(encoding='utf-8'))
        partner = rpc.execute('res.partner', 'read', [[state['partner_id']]], fields=['name'])[0]
        require(partner['name'] == state['marker'], 'El registro no sobrevivio a la recreacion del Pod')
        attachment = rpc.execute('ir.attachment', 'read', [[state['attachment_id']]], fields=['datas', 'store_fname'])[0]
        require(bool(attachment['datas']), 'El archivo del adjunto no esta disponible')
        digest = hashlib.sha256(base64.b64decode(attachment['datas'])).hexdigest()
        require(digest == state['content_sha256'], 'Cambio el contenido del archivo persistido')
        state['checks'].append({
            'stage': args.stage, 'record': 'ok', 'attachment': 'ok',
            'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        })
    state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'action': args.action, 'stage': args.stage, 'marker': state['marker'], 'status': 'passed'}))


if __name__ == '__main__':
    main()
