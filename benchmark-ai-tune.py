#!/usr/bin/env python3
"""Benchmark --ai-tune across multiple models.
Runs each model with heuristic baseline, then ai-tune, compares results.

Usage:
    python3 benchmark-ai-tune.py                    # All .gguf in ~/ai_models
    python3 benchmark-ai-tune.py model1.gguf model2.gguf
    python3 benchmark-ai-tune.py --rounds 4         # Fewer rounds (faster)
    python3 benchmark-ai-tune.py --skip mmproj      # Skip files matching pattern
"""

import argparse
import contextlib
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
LLM_SERVER = SCRIPT_DIR / "llm-server"
CACHE_DIR = Path.home() / ".cache" / "llm-server"
HISTORY_FILE = CACHE_DIR / "tune_history.jsonl"
RESULTS_FILE = SCRIPT_DIR / "benchmark-results.json"
PORT = 8081


def kill_port(port) -> None:
    """Kill anything on the port."""
    try:
        pids = (
            subprocess.check_output(
                ["lsof", "-t", f"-i:{port}"],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
        if pids:
            for pid in pids.split("\n"):
                with contextlib.suppress(ProcessLookupError, ValueError):
                    os.kill(int(pid), signal.SIGKILL)
            time.sleep(3)
    except subprocess.CalledProcessError:
        pass


def get_heuristic_baseline(model_path):
    """Run model with heuristic config, benchmark, return gen/pp tok/s."""
    kill_port(PORT)

    # Delete any existing tune cache for this model so we get pure heuristic
    for f in CACHE_DIR.glob("tune_*.json"):
        model_name = Path(model_path).name
        if model_name in f.name:
            backup = f.with_suffix(".json.bak")
            f.rename(backup)

    # Start server with heuristic config + benchmark mode
    proc = subprocess.Popen(
        ["bash", str(LLM_SERVER), str(model_path), "--benchmark"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    gen_tps = 0.0
    pp_tps = 0.0
    try:
        stdout, _ = proc.communicate(timeout=600)
        for line in stdout.split("\n"):
            if "gen" in line and "tok/s" in line and "pp" in line:
                # Parse: "Benchmark: gen=25.94 tok/s  pp=150.54 tok/s"
                parts = line.split()
                for p in parts:
                    if p.startswith("gen="):
                        with contextlib.suppress(ValueError):
                            gen_tps = float(p.split("=")[1])
                    elif p.startswith("pp="):
                        with contextlib.suppress(ValueError):
                            pp_tps = float(p.split("=")[1])
    except subprocess.TimeoutExpired:
        proc.kill()

    kill_port(PORT)
    return gen_tps, pp_tps


def run_ai_tune(model_path, rounds=8):
    """Run --ai-tune --retune, return best gen/pp tok/s."""
    kill_port(PORT)

    # Remove tune cache to force fresh tune from heuristic
    for f in CACHE_DIR.glob("tune_*.json"):
        model_name = Path(model_path).name
        if model_name in f.name:
            f.unlink()

    os.environ.copy()

    # Temporarily patch rounds if needed
    proc = subprocess.Popen(
        ["bash", str(LLM_SERVER), str(model_path), "--ai-tune", "--retune"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    baseline_gen = 0.0
    baseline_pp = 0.0
    best_gen = 0.0
    best_pp = 0.0
    best_name = "baseline"
    rounds_completed = 0

    try:
        stdout, _ = proc.communicate(timeout=7200)  # 2h max
        for line in stdout.split("\n"):
            if "Baseline:" in line:
                for p in line.split():
                    if p.startswith("gen="):
                        with contextlib.suppress(ValueError):
                            baseline_gen = float(p.split("=")[1])
                    elif p.startswith("pp="):
                        with contextlib.suppress(ValueError):
                            baseline_pp = float(p.split("=")[1])
            if "NEW BEST:" in line or "Result:" in line:
                rounds_completed += 1
                for p in line.split():
                    if p.startswith("gen="):
                        try:
                            g = float(p.split("=")[1])
                            best_gen = max(best_gen, g)
                        except ValueError:
                            pass
                    elif p.startswith("pp="):
                        try:
                            pp = float(p.split("=")[1])
                            if best_gen == g:
                                best_pp = pp
                        except ValueError:
                            pass
            if "CRASHED" in line:
                rounds_completed += 1
            if "wins!" in line:
                # Extract winner name: "AI Tune complete: <name> wins!"
                parts = line.split(":")
                if len(parts) > 1:
                    best_name = parts[-1].replace("wins!", "").strip()
            if "baseline wins" in line:
                best_name = "baseline"
                best_gen = baseline_gen
                best_pp = baseline_pp

    except subprocess.TimeoutExpired:
        proc.kill()

    kill_port(PORT)

    # If best is still 0 but baseline was measured, baseline won
    if best_gen == 0 and baseline_gen > 0:
        best_gen = baseline_gen
        best_pp = baseline_pp
        best_name = "baseline"

    return {
        "baseline_gen": baseline_gen,
        "baseline_pp": baseline_pp,
        "tuned_gen": best_gen,
        "tuned_pp": best_pp,
        "best_name": best_name,
        "rounds": rounds_completed,
    }


def restore_caches() -> None:
    """Restore any backed-up tune caches."""
    for f in CACHE_DIR.glob("tune_*.json.bak"):
        orig = f.with_suffix("")  # remove .bak
        if not orig.exists():
            f.rename(orig)
        else:
            f.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark --ai-tune across models")
    parser.add_argument(
        "models", nargs="*", help="Model paths (default: all in ~/ai_models)"
    )
    parser.add_argument(
        "--rounds", type=int, default=10, help="Tuning rounds (default: 10)"
    )
    parser.add_argument(
        "--skip", nargs="*", default=["mmproj"], help="Skip files matching patterns"
    )
    parser.add_argument(
        "--model-dir", default=str(Path.home() / "ai_models"), help="Model directory"
    )
    args = parser.parse_args()

    if args.models:
        models = [Path(m) for m in args.models]
    else:
        model_dir = Path(args.model_dir)
        models = sorted(model_dir.glob("*.gguf"))

    # Filter skips
    models = [m for m in models if not any(s in m.name for s in args.skip)]

    if not models:
        sys.exit(1)

    results = []

    for model in models:

        start = time.time()
        result = run_ai_tune(model, args.rounds)
        elapsed = time.time() - start

        gain_gen = 0
        gain_pp = 0
        if result["baseline_gen"] > 0:
            gain_gen = (
                (result["tuned_gen"] - result["baseline_gen"])
                / result["baseline_gen"]
                * 100
            )
        if result["baseline_pp"] > 0:
            gain_pp = (
                (result["tuned_pp"] - result["baseline_pp"])
                / result["baseline_pp"]
                * 100
            )

        result["model"] = model.name
        result["gain_gen_pct"] = round(gain_gen, 1)
        result["gain_pp_pct"] = round(gain_pp, 1)
        result["elapsed_min"] = round(elapsed / 60, 1)
        result["timestamp"] = datetime.utcnow().isoformat() + "Z"
        results.append(result)

    # Restore backed up caches
    restore_caches()

    # Print summary table
    for _r in results:
        pass

    sum(r["gain_gen_pct"] for r in results) / len(results) if results else 0

    # Save results
    with Path(RESULTS_FILE).open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
