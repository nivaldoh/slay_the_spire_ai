"""Windows side of battle checkpoints: run checkpoint_agent.js in the owned game with a config.

Runs under a Windows Python that has Frida (see checkpoint.FRIDA_PYTHON). Every agent message
goes to <output>/native.jsonl; <output>/ready marks a loaded agent. Stops when
<output>/STOP appears, the game exits or --seconds pass.
"""
import argparse
import json
import sys
import threading
import time
from pathlib import Path

import frida


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--agent", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=560)
    args = parser.parse_args()
    assert sys.platform == "win32"
    source = args.agent.read_text()
    marker = "const CONFIG = null;"
    assert source.count(marker) == 1
    source = source.replace(marker, "const CONFIG = " + args.config.read_text() + ";")
    device = frida.get_local_device()
    session = device.attach(args.pid)
    detached = threading.Event()
    with (args.output / "native.jsonl").open("x", buffering=1) as log:
        def on_message(message, data):
            row = (message["payload"] if message.get("type") == "send"
                   else {"event": "frida_error", "message": message})
            log.write(json.dumps({"wall_time": time.time(), **row}) + "\n")
            if row.get("event") == "ready":
                (args.output / "ready").write_text(str(args.pid))

        def on_detached(reason, crash):
            row = {"wall_time": time.time(), "event": "detached", "reason": reason}
            log.write(json.dumps(row) + "\n")
            detached.set()

        session.on("detached", on_detached)
        script = session.create_script(source)
        script.on("message", on_message)
        script.load()
        deadline = time.monotonic() + args.seconds
        stop = args.output / "STOP"
        while time.monotonic() < deadline and not detached.is_set() and not stop.exists():
            time.sleep(0.2)
        if not detached.is_set():
            script.unload()
            session.detach()


if __name__ == "__main__":
    main()
