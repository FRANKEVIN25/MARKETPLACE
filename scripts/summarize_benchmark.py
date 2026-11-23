"""Summarize Locust CSVs produced by run_benchmark.ps1.

Reports measured values only; does not infer scaling from missing runs.
"""

import argparse
import json
import math
from pathlib import Path
from statistics import median


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
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
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
        "error_pct": round(100 * failures / requests, 3),
        "measurement_seconds": duration,
        "average_ms": round(sum(entry["total_response_time"] for entry in entries) / requests, 2),
        "p95_ms": percentile(histogram, 0.95),
        "successful_rps": round((requests - failures) / duration, 3),
        "csv": str(folder / "run_stats.csv"),
        "timeline": str(folder / "infrastructure.csv"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-dir", type=Path, default=ROOT / ".lab" / "runs")
    args = parser.parse_args()
    runs = []
    for metadata_path in sorted(args.runs_dir.glob("*/metadata.json")):
        folder = metadata_path.parent
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if (metadata.get("job_succeeded") and (folder / "final.json").exists()
                and (folder / "timing.json").exists()):
            runs.append(load_run(folder))
    if not runs:
        raise SystemExit("No hay corridas completas en " + str(args.runs_dir))
    groups = {}
    for run in runs:
        key = (run["mode"], str(run["pods"]), run["users"], run["hpa"])
        groups.setdefault(key, []).append(run)
    lines = [
        "# Resultados medidos de Odoo",
        "",
        "Cada fila resume repeticiones equivalentes. p95 y operaciones exitosas/s son medianas.",
        "Locust cuenta las respuestas JSON-RPC con error como fallas aunque HTTP sea 200.",
        "",
        "| Modo | Pods | Usuarios | Repeticiones | p95 (ms) | Exitosas/s | Errores (%) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for key, group in sorted(groups.items(), key=lambda pair: (pair[0][0], pair[0][2], pair[0][1])):
        mode, pods, users, _ = key
        lines.append(
            f"| {mode} | {pods} | {users} | {len(group)} | "
            f"{median(item['p95_ms'] for item in group):.1f} | "
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
