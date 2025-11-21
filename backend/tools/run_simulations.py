# run_simulations.py
# Usage: python run_simulations.py --runs 10 --ticks 200 --outdir ../data/sim_runs
#
# This script loads backend/data/world_seed.json, runs the simulation headless N times,
# saves a stats CSV per run, and optionally writes a combined summary CSV.

import os
import argparse
from pathlib import Path
import shutil
import json
from world import World

def ensure_dir(p):
    os.makedirs(p, exist_ok=True)

def run_single(seed_file, ticks, out_csv_path):
    w = World(seed_file)
    for _ in range(ticks):
        w.step()
    # export CSV to out_csv_path
    w.export_stats_csv(out_file=out_csv_path)
    return out_csv_path

def aggregate_csvs(csv_paths, out_path):
    # simple concatenation with headers unified (assumes same header)
    if not csv_paths:
        return None
    header_written = False
    with open(out_path, "w", encoding="utf-8", newline='') as fw:
        for i, p in enumerate(csv_paths):
            with open(p, "r", encoding="utf-8") as fr:
                lines = fr.readlines()
            if not lines:
                continue
            # header is first line
            if not header_written:
                fw.write(lines[0])
                header_written = True
            # write body (skip header)
            fw.writelines(lines[1:])
    return out_path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=5, help="Number of simulation runs")
    parser.add_argument("--ticks", type=int, default=240, help="Ticks per run (e.g., 240 = 10 days if 24 ticks/day)")
    parser.add_argument("--seed", type=str, default="../data/world_seed.json", help="Path to seed JSON (relative to tools/)")
    parser.add_argument("--outdir", type=str, default="../data/sim_runs", help="Output directory for CSVs (relative to tools/)")
    parser.add_argument("--aggregate", action="store_true", help="Create aggregated CSV of all runs")
    args = parser.parse_args()

    tools_dir = Path(__file__).resolve().parent
    seed_file = (tools_dir / args.seed).resolve()
    out_dir = (tools_dir / args.outdir).resolve()
    ensure_dir(out_dir)

    csv_paths = []
    print(f"Running {args.runs} runs, each {args.ticks} ticks. Seed: {seed_file}")
    for i in range(1, args.runs + 1):
        out_csv = out_dir / f"sim_run_{i}.csv"
        if out_csv.exists():
            out_csv.unlink()
        print(f" Run {i} ...", end="", flush=True)
        run_single(str(seed_file), args.ticks, str(out_csv))
        csv_paths.append(str(out_csv))
        print(" done.")

    if args.aggregate:
        agg_path = out_dir / "aggregated.csv"
        if agg_path.exists():
            agg_path.unlink()
        aggregate_csvs(csv_paths, str(agg_path))
        print(f"Aggregated CSV created at {agg_path}")

    print("All runs finished. CSVs:", csv_paths)

if __name__ == "__main__":
    main()
