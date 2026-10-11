"""Supervise one explicitly configured local SFT job; never download or launch a game."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

FINALIZATION_SECONDS = 30


def available_mib() -> float:
    fields = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())
    return int(fields["MemAvailable"].split()[0]) / 1024


def gpu_used_mib() -> float:
    executable = shutil.which("nvidia-smi") or "/usr/lib/wsl/lib/nvidia-smi"
    result = subprocess.check_output(
        [executable, "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        text=True,
        timeout=2,
    )
    return float(result.splitlines()[0])


def stop_worker(process) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGINT)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)


def supervise(args) -> int:
    started = time.time()
    output = args.output.resolve()
    job_path = output / "job.json"
    if args.resume:
        job = json.loads(job_path.read_text())
        config = job["config"]
        deadline = job["deadline_unix"]
    else:
        if args.finalize:
            raise ValueError("--finalize requires --resume")
        if args.config is None:
            raise ValueError("A new job requires --config with every experiment budget")
        if output.exists():
            raise ValueError("Output already exists; use explicit --resume")
        config = json.loads(args.config.read_text())
        deadline = started + config["time_budget_seconds"]
    finalize_only = args.resume and (args.finalize or deadline <= started)
    watchdog_deadline = started + FINALIZATION_SECONDS if finalize_only else deadline
    environment = dict(
        os.environ,
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        HF_HUB_DISABLE_TELEMETRY="1",
        TOKENIZERS_PARALLELISM="false",
        CUBLAS_WORKSPACE_CONFIG=":4096:8",
    )
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", "--output", str(output)]
    if args.config is not None:
        command += ["--config", str(args.config.resolve())]
    if args.resume:
        command += ["--resume"]
    else:
        command += ["--started-unix", str(started)]
    if finalize_only:
        command += ["--finalize"]
    # Check before starting even the loader. No network or implicit fallback is allowed.
    minimum_ram = available_mib()
    maximum_gpu = None if finalize_only else gpu_used_mib()
    if minimum_ram < config.get("min_available_mib", 700):
        raise RuntimeError("Available RAM below training guard")
    if maximum_gpu is not None and maximum_gpu >= config.get("max_gpu_gib", 10) * 1024:
        raise RuntimeError("GPU memory guard reached")
    process = subprocess.Popen(command, env=environment, start_new_session=True)
    reason, polls = "worker_exit", 0
    try:
        while process.poll() is None:
            if job_path.exists():
                observed = json.loads(job_path.read_text())["deadline_unix"]
                if observed != deadline:
                    reason = "job_deadline_changed"
                    break
            if time.time() >= watchdog_deadline:
                reason = "finalization_deadline" if finalize_only else "deadline"
                break
            memory = available_mib()
            gpu = None if finalize_only else gpu_used_mib()
            minimum_ram = min(minimum_ram, memory)
            if gpu is not None:
                maximum_gpu = max(maximum_gpu, gpu)
            polls += 1
            if memory < config.get("min_available_mib", 700):
                reason = "low_ram"
                break
            if gpu is not None and gpu >= config.get("max_gpu_gib", 10) * 1024:
                reason = "gpu_memory"
                break
            time.sleep(min(0.5, max(0, watchdog_deadline - time.time())))
    except BaseException as error:
        reason = type(error).__name__
        raise
    finally:
        stop_worker(process)
        result = {
            "schema_version": 1,
            "stop_reason": reason,
            "exit_code": process.returncode,
            "started_unix": started,
            "deadline_unix": deadline,
            "supervision_deadline_unix": watchdog_deadline,
            "finalize_only": finalize_only,
            "elapsed_seconds": time.time() - started,
            "cleanup_overrun_seconds": max(0, time.time() - deadline),
            "minimum_available_mib": minimum_ram,
            "maximum_gpu_used_mib": maximum_gpu,
            "polls": polls,
            "scope": "Resource supervision; no gameplay evaluation",
        }
        if output.is_dir():
            # Keep each invocation, including interrupted/resumed supervision evidence.
            target = output / f"watchdog-{time.time_ns()}.json"
            target.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
        print(json.dumps(result, sort_keys=True), flush=True)
    return process.returncode if reason == "worker_exit" else 124 if reason == "deadline" else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--finalize", action="store_true", help="Export committed state using CPU only"
    )
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--started-unix", type=float, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        from spire.language_training import train_language

        config = json.loads(args.config.read_text()) if args.config else None
        result = train_language(
            args.output,
            config,
            resume=args.resume,
            started_unix=args.started_unix,
            finalize_only=args.finalize,
        )
        print(
            json.dumps(
                {
                    key: result[key]
                    for key in ("stop_reason", "updates", "charged_tokens", "artifact")
                    if key in result
                },
                sort_keys=True,
            ),
            flush=True,
        )
        return 0
    return supervise(args)


if __name__ == "__main__":
    raise SystemExit(main())
