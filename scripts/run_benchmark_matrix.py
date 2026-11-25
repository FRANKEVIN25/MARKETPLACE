"""Preview or execute the 36 fixed-replica runs. Execution is explicit and resumable."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = shutil.which('pwsh.exe') or shutil.which('powershell.exe')


class StepFailed(RuntimeError):
    def __init__(self, stdout):
        super().__init__('A step failed; the checkpoint is preserved and the matrix is incomplete')
        self.stdout = stdout


def run(arguments, *, capture=True):
    result = subprocess.run(arguments, cwd=ROOT, text=True, capture_output=capture,
                            encoding='utf-8', errors='replace')
    if capture:
        print(result.stdout, end='', flush=True)
        if result.stderr:
            print(result.stderr, file=sys.stderr, end='', flush=True)
    if result.returncode:
        raise StepFailed(result.stdout or '')
    return result.stdout or ''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--resume', type=Path)
    parser.add_argument('--mode', choices=('read', 'write'), default='read')
    args = parser.parse_args()
    cells = [{'pods': pods, 'users': users, 'repeat': repeat} for repeat in (1, 2, 3)
             for users in (20, 50, 100, 200) for pods in (1, 2, 3)]
    if not args.execute:
        print(json.dumps({'mode': args.mode, 'runs': len(cells), 'warmup_seconds': 30,
                          'measurement_seconds': 300, 'spawn_rate': 5, 'seed': 2026,
                          'expected_cells': cells,
                          'note': 'Preview only. No cluster changes and no load were started.'}, indent=2))
        return
    if not POWERSHELL:
        raise RuntimeError('PowerShell is required to control the Kubernetes laboratory')
    if run(['git', 'status', '--porcelain', '--untracked-files=no']).strip():
        raise RuntimeError('Commit or resolve tracked changes before the formal matrix')
    commit = run(['git', 'rev-parse', 'HEAD']).strip()
    if args.resume:
        checkpoint = args.resume.resolve()
        allowed = (ROOT / '.lab/matrices').resolve()
        if not checkpoint.is_relative_to(allowed):
            raise RuntimeError('Checkpoint must be inside .lab/matrices')
        study = json.loads(checkpoint.read_text(encoding='utf-8'))
        if study['commit'] != commit or study['mode'] != args.mode:
            raise RuntimeError('Commit or workload differs from the existing matrix')
    else:
        experiment = 'matrix-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        checkpoint = ROOT / '.lab/matrices' / (experiment + '.json')
        study = {'experiment_id': experiment, 'commit': commit, 'mode': args.mode,
                 'complete': False, 'cells': [{**cell, 'status': 'pending'} for cell in cells]}
    checkpoint.parent.mkdir(parents=True, exist_ok=True)

    def save():
        checkpoint.write_text(json.dumps(study, indent=2) + '\n', encoding='utf-8')

    save()
    for cell in study['cells']:
        if cell['status'] == 'complete':
            result = ROOT / '.lab/runs' / cell['run_id'] / 'metadata.json'
            if not result.exists() or not json.loads(result.read_text())['job_succeeded']:
                raise RuntimeError('A completed run is missing or invalid')
            continue
        if cell['status'] == 'failed' and args.mode == 'write':
            # A failed run may already have written drafts during ramp/warmup.
            # Clean only its own prefix before retrying the pending cell.
            run([POWERSHELL, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'scripts/kubernetes.ps1', '-Action', 'Forward'], capture=False)
            run([sys.executable, 'scripts/benchmark_dataset.py', 'reset-orders', '--run-id', cell['run_id']])
            run([sys.executable, 'scripts/benchmark_dataset.py', 'verify'])
            cell['status'] = 'pending'
            save()
        if cell['status'] == 'measured':
            run_id = cell['run_id']
        else:
            run([POWERSHELL, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'scripts/kubernetes.ps1',
                 '-Action', 'Scale', '-Replicas', str(cell['pods'])], capture=False)
            try:
                output = run([sys.executable, 'scripts/benchmark_runner.py', '--mode', args.mode,
                    '--pods', str(cell['pods']), '--users', str(cell['users']), '--repeat', str(cell['repeat']),
                    '--purpose', 'benchmark', '--experiment-id', study['experiment_id'],
                    '--duration-seconds', '300', '--warmup-seconds', '30', '--spawn-rate', '5', '--seed', '2026'])
            except StepFailed as error:
                failed = re.search(r'job\.batch/bench-([0-9]+) created', error.stdout)
                if failed:
                    cell.update({'status': 'failed', 'run_id': failed[1]})
                    cell.setdefault('failed_run_ids', []).append(failed[1])
                    save()
                raise
            match = re.search(r'job\.batch/bench-([0-9]+) created', output)
            if not match:
                raise RuntimeError('Missing run identifier')
            run_id = match[1]
        metadata = json.loads((ROOT / '.lab/runs' / run_id / 'metadata.json').read_text())
        signature = metadata['comparison_signature']
        if study.get('comparison_signature', signature) != signature:
            cell.update({'status': 'configuration_drift', 'run_id': run_id})
            save()
            raise RuntimeError('Configuration changed across matrix cells; do not combine these results')
        study['comparison_signature'] = signature
        if not metadata.get('job_succeeded'):
            raise RuntimeError('The saved measurement did not complete successfully')
        # Persist before cleanup: a failed cleanup must not rerun a valid cell.
        cell.update({'status': 'measured', 'run_id': run_id})
        save()
        if args.mode == 'write':
            run([POWERSHELL, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'scripts/kubernetes.ps1', '-Action', 'Forward'], capture=False)
            run([sys.executable, 'scripts/benchmark_dataset.py', 'reset-orders', '--run-id', run_id])
            run([sys.executable, 'scripts/benchmark_dataset.py', 'verify'])
        cell.update({'status': 'complete', 'run_id': run_id})
        save()
    study['complete'] = True
    save()
    run([sys.executable, 'scripts/summarize_benchmark.py', '--purpose', 'benchmark'])
    print('Matriz completa: ' + str(checkpoint))


if __name__ == '__main__':
    main()
