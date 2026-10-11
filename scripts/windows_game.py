"""Own one Windows JVM and stop it on controller EOF or a hard time limit."""

import argparse
import json
import math
import os
import subprocess
import sys
import threading
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", required=True)
    parser.add_argument("--loader", required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("--timeout", type=float, default=600)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("timeout must be positive and finite")
    game_dir = Path(args.game_dir)
    command = [
        str(game_dir / "jre/bin/java.exe"),
        "-Xmx1G",
        "-Dfile.encoding=UTF-8",
        "-jar",
        args.loader,
        "--skip-launcher",
        "--skip-intro",
        "--mods",
        "basemod,CommunicationMod",
    ]
    stop = threading.Event()

    def watch_controller() -> None:
        # EOF also means the WSL controller disappeared. Never leave an orphan JVM.
        os.read(sys.stdin.fileno(), 1)
        stop.set()

    with Path(args.log).open("wb") as log:
        process = subprocess.Popen(command, cwd=game_dir, stdout=log, stderr=subprocess.STDOUT)
        try:
            print(json.dumps({"pid": process.pid, "command": command}), flush=True)
            threading.Thread(target=watch_controller, daemon=True).start()
            deadline = time.monotonic() + args.timeout
            while process.poll() is None:
                if stop.wait(min(0.2, max(0, deadline - time.monotonic()))):
                    break
                if time.monotonic() >= deadline:
                    break
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        print(json.dumps({"exit_code": process.returncode}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
