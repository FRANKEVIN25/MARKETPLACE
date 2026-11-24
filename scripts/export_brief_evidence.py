"""Publish only selected non-secret evidence from the agreed brief validation."""

import csv
import json
from pathlib import Path
import shutil

from summarize_benchmark import load_run

ROOT = Path(__file__).resolve().parents[1]
RUNS = ('202611231848375800', '202611231849378000', '202611231850377000', '202611231840403600')
INVALID_HPA = ('202611231828534800', '202611231832012000', '202611231834558700')
DEST = ROOT / 'docs/evidence/frank-validacion-breve'


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    runs = []
    for run_id in RUNS:
        source = ROOT / '.lab/runs' / run_id
        destination = DEST / run_id
        destination.mkdir(exist_ok=True)
        for name in ('metadata.json', 'timing.json', 'final.json', 'run_stats.csv',
                     'run_failures.csv', 'infrastructure.csv', 'pods_timeline.json'):
            shutil.copyfile(source / name, destination / name)
        row = load_run(source)
        row['csv'] = run_id + '/run_stats.csv'
        row['timeline'] = run_id + '/infrastructure.csv'
        runs.append(row)
    integration = json.loads((ROOT / '.lab/integration-result.json').read_text(encoding='utf-8'))
    if not integration['valid']:
        raise RuntimeError('Integration did not pass')
    write(DEST / 'integration.json', integration)
    invalid = []
    for run_id in INVALID_HPA:
        source = ROOT / '.lab/runs' / run_id
        metadata = json.loads((source / 'metadata.json').read_text(encoding='utf-8'))
        item = {'run_id': run_id, 'job_succeeded': metadata['job_succeeded'], 'users': metadata['users'],
                'reason': 'session preparation/concurrency gate failed; excluded from measured results'}
        if (source / 'timing.json').exists():
            item['timing'] = json.loads((source / 'timing.json').read_text())
        invalid.append(item)
    write(DEST / 'excluded-attempts.json', invalid)
    shutil.copyfile(ROOT / '.lab/hpa-after-load.json', DEST / 'hpa-after-load.json')
    summary = {'scope': 'brief validation only; full formal matrix not executed',
               'date_lima': '2026-11-23', 'runs': runs, 'integration_valid': integration['valid'],
               'statistics_source': 'final.json + timing.json; raw CSV is a periodic snapshot and can lag the final JSON',
               'source_state': 'development runs based on a5873ab; tracked edits and script hashes preserved in metadata',
               'tests': {'benchmark_helpers': 7, 'django_sync': 6, 'existing_order_api': 1},
               'matrix_resume_simulations': ['do not rerun a measured cell', 'clean failed writes before retry'],
               'excluded_hpa_attempts': INVALID_HPA}
    write(DEST / 'summary.json', summary)
    with (DEST / 'measured_summary.csv').open('w', encoding='utf-8', newline='') as stream:
        fields = ['run_id', 'purpose', 'pods', 'users', 'measurement_seconds', 'requests',
                  'failures', 'error_pct', 'p95_ms', 'successful_rps', 'comparison_eligible']
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: row[key] for key in fields} for row in runs)
    print(DEST)


if __name__ == '__main__':
    main()
