"""Run a measured Locust window inside the isolated Minikube laboratory."""

import argparse
import configparser
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import time
from datetime import datetime, timezone

from benchmark_protocol import VERSION, comparison_policy, fingerprint

ROOT = Path(__file__).resolve().parents[1]
KUBECTL = ROOT / '.tools' / 'kubectl.exe'
PREFIX = [str(KUBECTL), '--kubeconfig', str(ROOT / '.lab/kubeconfig'),
          '--context', 'ecomparts-k8s', '--namespace', 'ecomparts']
LOCUST_IMAGE = 'locustio/locust:2.47.0'
LOAD_RESOURCES = {'requests': {'cpu': '250m', 'memory': '256Mi'},
                  'limits': {'cpu': '1000m', 'memory': '1Gi'}}


def utc():
    return datetime.now(timezone.utc).isoformat()


def command(args, check=True):
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True,
                            encoding='utf-8', errors='replace')
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'Command failed')
    return result


def kube(*args, check=True):
    return command(PREFIX + list(args), check=check)


def obj(*args):
    return json.loads(kube(*args).stdout)


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def container(pod, name):
    spec = next(item for item in pod['spec']['containers'] if item['name'] == name)
    status = next(item for item in pod['status']['containerStatuses'] if item['name'] == name)
    return {'image': spec['image'], 'image_id': status.get('imageID'), 'resources': spec['resources']}


def snapshot():
    nodes = obj('get', 'nodes', '-o', 'json')['items']
    if len(nodes) != 1:
        raise RuntimeError('This shared-storage experiment requires exactly one node')
    deployment = obj('get', 'deployment', 'odoo', '-o', 'json')
    pods = obj('get', 'pods', '-l', 'app.kubernetes.io/name=odoo', '-o', 'json')['items']
    pods = [pod for pod in pods if not pod['metadata'].get('deletionTimestamp')]
    configs = [container(pod, 'odoo') for pod in pods]
    if not configs or any(value != configs[0] for value in configs):
        raise RuntimeError('Odoo images or resources differ between Pods')
    template = obj('get', 'configmap', 'odoo-config', '-o', 'json')['data']['odoo.conf.tpl']
    config = configparser.RawConfigParser()
    config.read_string(template)
    options = {key: config.get('options', key) for key in ('workers', 'max_cron_threads', 'db_maxconn', 'data_dir')}
    if options['workers'] != '2' or options['max_cron_threads'] != '0':
        raise RuntimeError('Unexpected workers or cron configuration')
    postgres = obj('get', 'pod', 'postgres-0', '-o', 'json')
    maximum = kube('exec', 'postgres-0', '--', 'sh', '-c',
                   'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SHOW max_connections"').stdout.strip()
    service = obj('get', 'service', 'odoo', '-o', 'json')
    node = nodes[0]
    # The Docker driver can expose the VM capacity to kubelet even though the
    # node container has a smaller cgroup budget. Record both for comparisons.
    host_limits = json.loads(command(['docker', 'inspect', 'ecomparts-k8s', '--format',
                                     '{{json .HostConfig}}']).stdout)
    configuration = {
        'node': {'name': node['metadata']['name'], 'capacity': node['status']['capacity'],
                 'allocatable': node['status']['allocatable'],
                 'kubelet_version': node['status']['nodeInfo']['kubeletVersion']},
        'node_container_limits': {key: host_limits.get(key) for key in
                                  ('Memory', 'NanoCpus', 'CpuQuota', 'CpuPeriod', 'CpusetCpus')},
        'odoo': {**configs[0], 'options': options, 'configuration_sha256': hashlib.sha256(template.replace('\r\n', '\n').encode()).hexdigest(),
                 'strategy': deployment['spec']['strategy'], 'session_affinity': service['spec'].get('sessionAffinity', 'None')},
        'postgres': {**container(postgres, 'postgres'), 'max_connections': maximum},
        'load_generator': {'image': LOCUST_IMAGE, 'resources': LOAD_RESOURCES},
    }
    return configuration, deployment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('read', 'write'), default='read')
    parser.add_argument('--users', type=int, default=20)
    parser.add_argument('--pods', type=int, choices=(1, 2, 3), default=1)
    parser.add_argument('--repeat', type=int, default=1)
    parser.add_argument('--duration-seconds', type=int, default=300)
    parser.add_argument('--warmup-seconds', type=int, default=30)
    parser.add_argument('--spawn-rate', type=int, default=5)
    parser.add_argument('--seed', type=int, default=2026)
    parser.add_argument('--purpose', choices=('smoke', 'benchmark', 'hpa', 'availability'), default='smoke')
    parser.add_argument('--experiment-id', default='manual')
    parser.add_argument('--hpa', action='store_true')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', args.experiment_id):
        parser.error('Experiment ID must contain only letters, numbers, underscore or dash')
    if not 1 <= args.users <= 500 or not 1 <= args.spawn_rate <= 100 or not 1 <= args.repeat <= 20:
        parser.error('Users, spawn rate or repetition outside laboratory bounds')
    if not 30 <= args.duration_seconds <= 3600 or not 0 <= args.warmup_seconds <= 600:
        parser.error('Invalid measurement or warmup duration')
    tracked = command(['git', 'status', '--porcelain', '--untracked-files=no']).stdout.splitlines()
    if args.purpose == 'benchmark' and (tracked or args.warmup_seconds < 30 or args.duration_seconds < 300 or args.experiment_id == 'manual'):
        raise RuntimeError('Formal runs require a clean tracked tree, warmup >=30s and measurement >=300s')
    configuration, deployment = snapshot()
    hpas = obj('get', 'hpa', '-o', 'json')['items']
    if bool(hpas) != args.hpa:
        raise RuntimeError('HPA state does not match the requested experiment')
    if not args.hpa and (deployment['spec']['replicas'] != args.pods or deployment['status'].get('readyReplicas', 0) != args.pods):
        raise RuntimeError('Prepare the requested fixed replica count first')
    active = [job for job in obj('get', 'jobs', '-o', 'json')['items']
              if job['metadata']['name'].startswith('bench-') and job['status'].get('active', 0)]
    if active:
        raise RuntimeError('Another load run is active')
    run_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(time.time_ns() % 10000).zfill(4)
    folder = ROOT / '.lab' / 'runs' / run_id
    folder.mkdir(parents=True)
    source = folder / 'source'
    source.mkdir()
    for name in ('locustfile.py', 'verify_odoo_lab.py', 'benchmark_protocol.py', 'benchmark_runner.py'):
        (source / name).write_bytes((ROOT / 'scripts' / name).read_bytes().replace(b'\r\n', b'\n'))
    job_name = 'bench-' + run_id
    cmap_name = 'benchmark-' + run_id
    scripts = obj('create', 'configmap', cmap_name, '--from-file=scripts/locustfile.py',
                  '--from-file=scripts/verify_odoo_lab.py', '--from-file=scripts/benchmark_protocol.py',
                  '--dry-run=client', '-o', 'json')
    scripts['immutable'] = True
    save(folder / 'configmap.json', scripts)
    kube('apply', '-f', str(folder / 'configmap.json'))
    locust_args = ['locust', '-f', '/mnt/locust/locustfile.py', '--headless', '-H', 'http://odoo:8069',
                  '-u', str(args.users), '-r', str(args.spawn_rate), '--csv', '/results/run',
                  '--csv-full-history', '--json-file', '/results/final', '--only-summary', '--exit-code-on-error', '0']
    environment = {'BENCH_MODE': args.mode, 'BENCH_RUN_ID': run_id, 'BENCH_USERS': str(args.users),
                   'BENCH_SPAWN_RATE': str(args.spawn_rate), 'BENCH_WARMUP_SECONDS': str(args.warmup_seconds),
                   'BENCH_MEASURE_SECONDS': str(args.duration_seconds), 'BENCH_SEED': str(args.seed),
                   'BENCH_TIMING_FILE': '/results/timing.json', 'BENCH_PHASE_FILE': '/results/phase.json'}
    job = {'apiVersion': 'batch/v1', 'kind': 'Job', 'metadata': {'name': job_name, 'namespace': 'ecomparts'},
           'spec': {'backoffLimit': 0, 'activeDeadlineSeconds': math.ceil(args.users/args.spawn_rate)+args.warmup_seconds+args.duration_seconds+600,
                    'template': {'metadata': {'labels': {'app.kubernetes.io/name': 'benchmark-load'}},
                                 'spec': {'restartPolicy': 'Never', 'containers': [{
                                     'name': 'locust', 'image': LOCUST_IMAGE,
                                     'command': ['sh', '-c'], 'args': [' '.join(locust_args)+'; code=$?; printf "%s" "$code" > /results/exit_code; sleep 600'],
                                     'envFrom': [{'configMapRef': {'name': 'odoo-config'}}, {'secretRef': {'name': 'ecomparts-secrets'}}],
                                     'env': [{'name': key, 'value': value} for key, value in environment.items()],
                                     'resources': LOAD_RESOURCES,
                                     'volumeMounts': [{'name': 'scripts', 'mountPath': '/mnt/locust', 'readOnly': True}, {'name': 'results', 'mountPath': '/results'}]}],
                                          'volumes': [{'name': 'scripts', 'configMap': {'name': cmap_name}}, {'name': 'results', 'emptyDir': {}}]}}}}
    save(folder / 'job.json', job)
    metadata = {'protocol_version': VERSION, 'run_id': run_id, 'commit': command(['git', 'rev-parse', 'HEAD']).stdout.strip(),
                'working_tree_status': tracked, 'mode': args.mode, 'purpose': args.purpose, 'users': args.users,
                'experiment_id': args.experiment_id,
                'pods_expected': 'HPA' if args.hpa else args.pods, 'repeat': args.repeat, 'hpa': args.hpa,
                'spawn_rate': args.spawn_rate, 'duration_seconds': args.duration_seconds, 'warmup_seconds': args.warmup_seconds,
                'seed': args.seed, 'company_weights': 'A:B:C = 1:2:3 largest remainder', 'read_mix': 'catalogue:stock = 3:2',
                'request_connection': 'close; same cookie across new connections to Service',
                'locust_script_sha256': sha(ROOT / 'scripts/locustfile.py'),
                'protocol_script_sha256': sha(ROOT / 'scripts/benchmark_protocol.py'),
                'runner_script_sha256': sha(Path(__file__)), 'configuration': configuration,
                'started_at_utc': utc(), 'job_succeeded': False}
    save(folder / 'metadata.json', metadata)
    print('job.batch/'+job_name+' created', flush=True)
    pod_name, samples, pod_events, first_traffic = None, [], [], {}
    try:
        kube('apply', '-f', str(folder / 'job.json'))
        deadline = time.monotonic()+math.ceil(args.users/args.spawn_rate)+args.warmup_seconds+args.duration_seconds+360
        finished = False
        while time.monotonic() < deadline:
            time.sleep(5)
            job_pods = obj('get', 'pods', '-l', 'batch.kubernetes.io/job-name='+job_name, '-o', 'json')['items']
            if job_pods:
                pod_name = job_pods[0]['metadata']['name']
                if job_pods[0]['status'].get('containerStatuses'):
                    configuration['load_generator']['image_id'] = container(job_pods[0], 'locust')['image_id']
            current = obj('get', 'deployment', 'odoo', '-o', 'json')
            if not args.hpa and current['spec']['replicas'] != args.pods:
                raise RuntimeError('Desired replicas changed during the fixed run')
            pods = obj('get', 'pods', '-l', 'app.kubernetes.io/name=odoo', '-o', 'json')['items']
            ready = [{'name': pod['metadata']['name'], 'uid': pod['metadata']['uid'], 'created_at_utc': pod['metadata']['creationTimestamp'],
                      'ready': any(c['type'] == 'Ready' and c['status'] == 'True' for c in pod['status'].get('conditions', [])),
                      'terminating': bool(pod['metadata'].get('deletionTimestamp'))} for pod in pods]
            now = utc()
            pod_events.append({'at_utc': now, 'pods': ready})
            if args.hpa:
                for state in ready:
                    name = state['name']
                    if state['ready'] and name not in first_traffic:
                        logs = kube('logs', name, '--timestamps', '--since-time='+metadata['started_at_utc'], '--tail=2000', check=False).stdout
                        matches = [line for line in logs.splitlines() if re.search(r'POST /web/dataset/call_kw.* 200 ', line)]
                        if matches:
                            first_traffic[name] = {'first_observed_post_200_at_utc': matches[0].split()[0], 'observed_at_utc': now}
            tops = kube('top', 'pods', '--no-headers', check=False).stdout.strip()
            connections = kube('exec', 'postgres-0', '--', 'sh', '-c',
                               'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database()"', check=False).stdout.strip()
            hpa = obj('get', 'hpa', '-o', 'json')['items']
            if not args.hpa and hpa:
                raise RuntimeError('An HPA appeared during the fixed run')
            samples.append({'timestamp_utc': now, 'desired_replicas': current['spec']['replicas'],
                            'ready_replicas': current['status'].get('readyReplicas', 0), 'postgres_connections': connections,
                            'pod_metrics': tops.replace('\n', ' | '),
                            'hpa_status': json.dumps(hpa[0].get('status', {})) if hpa else ''})
            if pod_name and kube('exec', pod_name, '--', 'test', '-f', '/results/exit_code', check=False).returncode == 0:
                finished = True
                break
            state = obj('get', 'job', job_name, '-o', 'json')
            if state['status'].get('failed', 0):
                break
        if not finished:
            raise RuntimeError('Locust did not finish its measurement window')
        for name in ('run_stats.csv', 'run_stats_history.csv', 'run_failures.csv', 'run_exceptions.csv', 'final.json', 'timing.json', 'phase.json'):
            (folder / name).write_text(kube('exec', pod_name, '--', 'cat', '/results/'+name).stdout, encoding='utf-8')
        (folder / 'locust.log').write_text(kube('logs', pod_name).stdout, encoding='utf-8')
        exit_code = kube('exec', pod_name, '--', 'cat', '/results/exit_code').stdout.strip()
        timing = json.loads((folder / 'timing.json').read_text())
        final_configuration, _ = snapshot()
        if any(configuration[key] != final_configuration[key] for key in ('node', 'node_container_limits', 'odoo', 'postgres')):
            raise RuntimeError('The node, application or database configuration changed during measurement')
        metadata.update({'locust_exit_code': exit_code, 'finished_at_utc': utc(),
                         'job_succeeded': exit_code == '0' and timing.get('valid', False),
                         'comparison_signature': fingerprint(configuration, comparison_policy(metadata)),
                         'first_observed_traffic': first_traffic})
        if not metadata['job_succeeded']:
            raise RuntimeError('The preparation or concurrency gate failed; this is not a valid measured run')
        print('Corrida guardada en '+str(folder), flush=True)
    finally:
        save(folder / 'metadata.json', metadata)
        save(folder / 'pods_timeline.json', pod_events)
        if samples:
            with (folder / 'infrastructure.csv').open('w', newline='', encoding='utf-8') as stream:
                writer = csv.DictWriter(stream, fieldnames=list(samples[0]))
                writer.writeheader()
                writer.writerows(samples)
        kube('delete', 'job', job_name, '--ignore-not-found=true', check=False)
        kube('delete', 'configmap', cmap_name, '--ignore-not-found=true', check=False)


if __name__ == '__main__':
    main()
