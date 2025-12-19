"""
compare_methods_resource_analysis.py
------------------------------------

A utility script to compare *Loris* and *Lam4Inv* on **time**, **input tokens**, and **output tokens**
using the raw experiment outputs produced by the original analysis scripts you shared.

Usage (example):
    python compare_methods_resource_analysis.py \
        --loris_json   Result/Loris/loris_results.json \
        --lam_dir      Result/GPT41minifull \
        --benchmarks   /home/tcli/loop-invariant-gen-experiments/experiments/finalbenchmark.txt \
        --out_dir      analysis_outputs

The script produces two artefacts inside *out_dir*:
    1. ``resource_summary.csv``  – one-row CSV giving the overall
       average resource consumption on the **intersection** of benchmarks both
       methods solved.
    2. ``success_vs_resource.png`` – a plot with two cumulative curves whose
       X-axis is *resource consumed* (default: **time in seconds**) and Y-axis
       is the *number of successful attempts* (each of the five independent
       runs counts).

You can switch the resource used on the X-axis via ``--x_metric`` ("time",
"input_tokens", or "output_tokens").

© 2025 – Feel free to adapt to your directory layout or extend the CSV with
per-benchmark information.
"""

import argparse
import json
import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt

###############################################################################
# --------------------------- Parsing helpers --------------------------------#
###############################################################################

def _append(d: Dict[str, List], key: str, val):
    if key not in d:
        d[key] = []
    d[key].append(val)

def parse_loris_results(loris_json_path: Path) -> Dict[str, Dict[str, List[float]]]:
    """Return mapping: benchmark -> {'time': [...], 'input': [...], 'output': [...]}."""
    data = json.loads(loris_json_path.read_text().strip().strip(','))
    out: Dict[str, Dict[str, List[float]]] = {}
    for entry in data:
        if not entry.get("valid", False):
            continue
        if int(entry.get("success_rate", "0/0").split("/")[0]) == 0:
            # Loris never succeeded on this benchmark
            continue
        bench = entry["benchmark"].split("../final_benchmarks/")[-1]
        for att in entry["detailed_data"]:
            if att["isSuccess"]:
                _append(out.setdefault(bench, {}), "time", float(att["time"]))
                _append(out[bench], "input", int(att["input_token"]))
                _append(out[bench], "output", int(att["output_token"]))
    return out

time_re = re.compile(r"Time cost is\s*:\s*(\d+(?:\.\d+)?)")
proposal_re = re.compile(r"The proposal times is\s*:\s*(\d+(?:\.\d+)?)")
input_tok_re = re.compile(r"The input token is\s*:\s*(\d+)")
output_tok_re = re.compile(r"The output token is\s*:\s*(\d+)")

def parse_lam_logs(lam_dir: Path, benchmarks: List[str]) -> Dict[str, Dict[str, List[float]]]:
    """Parse 5-run Lam4Inv logs; return same structure as *parse_loris_results*."""
    out: Dict[str, Dict[str, List[float]]] = {}
    for bench in benchmarks:
        for rep in range(5):
            fp = lam_dir / f"{bench}_{rep}.txt"
            if not fp.exists():
                continue
            txt = fp.read_text()
            if proposal_re.search(txt) is None:
                # unsuccessful attempt
                continue
            time_m = time_re.search(txt)
            in_m = input_tok_re.search(txt)
            out_m = output_tok_re.search(txt)
            if not (time_m and in_m and out_m):
                continue  # malformed line
            _append(out.setdefault(bench, {}), "time", float(time_m.group(1)))
            _append(out[bench], "input", int(in_m.group(1)))
            _append(out[bench], "output", int(out_m.group(1)))
    return out

###############################################################################
# ------------------------ Metric aggregation --------------------------------#
###############################################################################

def per_benchmark_means(raw: Dict[str, Dict[str, List[float]]]) -> Dict[str, Tuple[float, float, float]]:
    """Return bench -> (mean_time, mean_input_tokens, mean_output_tokens)."""
    means = {}
    for b, metrics in raw.items():
        if not metrics:
            continue
        mean_time = sum(metrics["time"]) / len(metrics["time"])
        mean_in   = sum(metrics["input"]) / len(metrics["input"])
        mean_out  = sum(metrics["output"]) / len(metrics["output"])
        means[b] = (mean_time, mean_in, mean_out)
    return means

###############################################################################
# ------------------------ Plotting helper -----------------------------------#
###############################################################################

def cumulative_success_curve(values: List[float]):
    """Return (x, y) sorted by *x* where y[i] = i+1 (1-based cumulative count)."""
    x_sorted = sorted(values)
    y = list(range(1, len(x_sorted) + 1))
    return x_sorted, y

###############################################################################
# --------------------------------- Main -------------------------------------#
###############################################################################

def main():
    parser = argparse.ArgumentParser(description="Compare Loris vs Lam4Inv resource consumption.")
    parser.add_argument("--loris_json", required=True, type=Path, help="Path to Loris JSON result file.")
    parser.add_argument("--lam_dir", required=True, type=Path, help="Directory containing Lam4Inv *_{rep}.txt logs.")
    parser.add_argument("--benchmarks", required=True, type=Path, help="Path to benchmark list (one per line).")
    parser.add_argument("--out_dir", default=Path("."), type=Path, help="Output directory for CSV & plot.")
    parser.add_argument("--x_metric", choices=["time", "input", "output"], default="time", help="Which resource to place on X-axis for the cumulative plot.")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    benchmarks = [l.strip() for l in args.benchmarks.read_text().splitlines() if l.strip()]

    loris_raw = parse_loris_results(args.loris_json)
    lam_raw   = parse_lam_logs(args.lam_dir, benchmarks)

    common = set(loris_raw).intersection(lam_raw)
    if not common:
        print("[!] No common solved benchmarks – nothing to compare.")
        return

    loris_means = per_benchmark_means({b: loris_raw[b] for b in common})
    lam_means   = per_benchmark_means({b: lam_raw[b]   for b in common})

    def _overall(means: Dict[str, Tuple[float, float, float]]):
        ts, ins, outs = zip(*means.values())
        return sum(ts) / len(ts), sum(ins) / len(ins), sum(outs) / len(outs)

    loris_overall = _overall(loris_means)
    lam_overall   = _overall(lam_means)

    # ------------------------ Save summary CSV ------------------------------ #
    csv_path = args.out_dir / "resource_summary.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Method", "Benchmarks", "Avg_Time(s)", "Avg_Input_Tokens", "Avg_Output_Tokens"])
        writer.writerow(["Loris", len(common), *[f"{v:.4f}" for v in loris_overall]])
        writer.writerow(["Lam4Inv", len(common), *[f"{v:.4f}" for v in lam_overall]])
    print(f"✓ Summary CSV written to {csv_path}")

    # --------------------- Build success-vs-resource plot ------------------- #
    loris_vals = [v for b in common for v in loris_raw[b][args.x_metric]]
    lam_vals   = [v for b in common for v in lam_raw[b][args.x_metric]]

    fig = plt.figure(figsize=(6, 4))
    x_loris, y_loris = cumulative_success_curve(loris_vals)
    x_lam,   y_lam   = cumulative_success_curve(lam_vals)
    plt.step(x_loris, y_loris, where="post", label="Loris")
    plt.step(x_lam,   y_lam,   where="post", label="Lam4Inv")
    plt.xlabel({"time": "Time (s)", "input": "Input tokens", "output": "Output tokens"}[args.x_metric])
    plt.ylabel("Successful attempts (cumulative)")
    plt.legend()
    plt.title("Success attempts vs. resource consumption")
    plt.tight_layout()
    plot_path = args.out_dir / "success_vs_resource.png"
    plt.savefig(plot_path, dpi=300)
    print(f"✓ Plot written to {plot_path}")

if __name__ == "__main__":
    main()
