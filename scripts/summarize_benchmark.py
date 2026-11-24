"""Summarize Locust CSVs produced by run_benchmark.ps1.

Reports measured values only; does not infer scaling from missing runs.
"""

import argparse
import json
import math
from pathlib import Path
from statistics import median
from benchmark_protocol import company_plan, comparison_policy, fingerprint


ROOT = Path(__file__).resolve().parents[1]


def percentile(histogram, percent):
    total = sum(histogram.values())
    target = math.ceil(total * percent)
    seen = 0
    for bucket, count in sorted(histogram.items()):
        seen += count
        if seen >= target:
            return bucket
    raise ValueError("Histograma de latencias vacio")


def load_run(folder):
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8-sig"))
    entries = json.loads((folder / "final.json").read_text(encoding="utf-8"))
    timing = json.loads((folder / "timing.json").read_text(encoding="utf-8"))
    expected = {"catalogue", "stock"} if metadata["mode"] == "read" else {"order/create"}
    if {entry["name"] for entry in entries} != expected:
        raise ValueError(f"Operaciones inesperadas en {folder}")
    requests = sum(entry["num_requests"] for entry in entries)
    failures = sum(entry["num_failures"] for entry in entries)
    if requests == 0:
        raise ValueError(f"Corrida sin solicitudes medidas: {folder}")
    duration = timing["measurement_seconds"]
    if duration <= 0:
        raise ValueError(f"Tiempo medido invalido: {folder}")
    version = metadata.get('protocol_version', 1)
    eligible = False
    if version >= 2:
        from collections import Counter
        planned = Counter(company_plan(metadata['users']))
        if (not timing.get('valid') or timing.get('prepared_users') != metadata['users']
                or timing.get('minimum_users_during_measurement') != metadata['users']
                or any(timing.get('company_users', {}).get(letter, 0) != planned[letter] for letter in 'ABC')
                or timing.get('setup_failures') != 0
                or abs(duration-metadata['duration_seconds']) > 2):
            raise ValueError(f'Preparacion o concurrencia no verificadas: {folder}')
        signature = fingerprint(metadata['configuration'], comparison_policy(metadata))
        if signature != metadata.get('comparison_signature'):
            raise ValueError(f'La firma de configuracion no coincide: {folder}')
        eligible = (metadata.get('purpose') == 'benchmark' and not metadata.get('working_tree_status')
                    and metadata['duration_seconds'] >= 300 and metadata['warmup_seconds'] >= 30)
    else:
        signature = 'legacy-' + metadata['run_id']
    histogram = {}
    for entry in entries:
        for bucket, count in entry["response_times"].items():
            value = int(bucket)
            histogram[value] = histogram.get(value, 0) + count
    return {
        "run_id": metadata["run_id"], "commit": metadata["commit"],
        "mode": metadata["mode"], "pods": metadata["pods_expected"],
        "hpa": metadata["hpa"], "users": metadata["users"],
        "repeat": metadata["repeat"], "requests": requests, "failures": failures,
        'purpose': metadata.get('purpose', 'legacy'), 'protocol_version': version,
        'comparison_signature': signature, 'comparison_eligible': eligible,
        'experiment_id': metadata.get('experiment_id', 'legacy'),
        "error_pct": round(100 * failures / requests, 3),
        "measurement_seconds": duration,
        "average_ms": round(sum(entry["total_response_time"] for entry in entries) / requests, 2),
        "p95_ms": percentile(histogram, 0.95) if histogram else None,
        "successful_rps": round((requests - failures) / duration, 3),
        "csv": str(folder / "run_stats.csv"),
        "timeline": str(folder / "infrastructure.csv"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-dir", type=Path, default=ROOT / ".lab" / "runs")
    parser.add_argument('--purpose', choices=('all', 'benchmark', 'smoke', 'hpa', 'availability'), default='all')
    args = parser.parse_args()
    runs = []
    for metadata_path in sorted(args.runs_dir.glob("*/metadata.json")):
        folder = metadata_path.parent
        metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
        if args.purpose != 'all' and metadata.get('purpose') != args.purpose:
            continue
        if (metadata.get("job_succeeded") and (folder / "final.json").exists()
                and (folder / "timing.json").exists()):
            runs.append(load_run(folder))
    if not runs:
        raise SystemExit("No hay corridas completas en " + str(args.runs_dir))
    groups = {}
    seen_repeats = set()
    for run in runs:
        key = (run['comparison_signature'], run['purpose'], run["mode"], str(run["pods"]), run["users"], run["hpa"])
        if run['comparison_eligible']:
            repeat_key = (*key, run['repeat'])
            if repeat_key in seen_repeats:
                raise ValueError('Repeticion formal duplicada: ' + run['run_id'])
            seen_repeats.add(repeat_key)
        groups.setdefault(key, []).append(run)
    lines = [
        "# Resultados medidos de Odoo",
        "",
        "Cada fila conserva una familia de configuracion. p95 y operaciones exitosas/s son medianas de las corridas de esa fila.",
        "Las pruebas smoke, availability, hpa y legacy no completan la matriz formal.",
        "Locust cuenta las respuestas JSON-RPC con error como fallas aunque HTTP sea 200.",
        "",
        "| Tipo | Familia | Modo | Pods | Usuarios | Corridas | p95 (ms) | Exitosas/s | Errores (%) |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for key, group in sorted(groups.items(), key=lambda pair: (pair[0][1], pair[0][2], pair[0][4], pair[0][3])):
        signature, purpose, mode, pods, users, _ = key
        p95s = [item['p95_ms'] for item in group if item['p95_ms'] is not None]
        p95 = f'{median(p95s):.1f}' if p95s else 'sin muestras'
        lines.append(
            f"| {purpose} | {signature[:12]} | {mode} | {pods} | {users} | {len(group)} | "
            f"{p95} | "
            f"{median(item['successful_rps'] for item in group):.2f} | "
            f"{median(item['error_pct'] for item in group):.2f} |"
        )
    lines.extend(["", "## Corridas", ""])
    for run in runs:
        lines.append(
            f"- {run['run_id']}: commit {run['commit'][:12]}, repeticion {run['repeat']}, "
            f"{run['requests']} solicitudes, {run['failures']} errores, "
            f"CSV: {run['csv']}, metricas: {run['timeline']}"
        )
    output = args.runs_dir / "summary.md"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (args.runs_dir / "summary.json").write_text(json.dumps(runs, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
