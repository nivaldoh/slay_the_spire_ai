"""Preview or create one expiring WH3 host, trying priced regions on capacity errors.

Default is read-only. See docs/twwarhammer3/gcp-client-setup.md for prerequisites.
Reference: SkyPilot sky/provision/provisioner.py stops failover when cleanup is uncertain;
Google's resource-availability guide distinguishes stockouts from quota/configuration errors.
"""

import argparse
import json
import math
import re
import subprocess
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "wh3-benchmark"
LOCATION = "us-central1"
MACHINE = "g2-standard-4"
GPU = "nvidia-l4-vws"
QUOTES = ROOT / "configs/twwarhammer3/gcp-regions.json"
BOOTSTRAP = ROOT / "scripts/gcp/windows-bootstrap.ps1"
CLEANUP = ROOT / "scripts/gcp/cleanup.yaml"
STOCKOUT = re.compile(r"^code: ZONE_RESOURCE_POOL_EXHAUSTED(?:_WITH_DETAILS)?\s*$", re.M)


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamps need a timezone")
    return parsed.astimezone(UTC)


def positive(value):
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError("Costs must be finite and nonnegative")
    return number


class CommandError(RuntimeError):
    def __init__(self, result):
        super().__init__(result.stderr.strip())
        self.result = result


class GCloud:
    def __init__(self, output=None):
        self.output = output
        self.sequence = 0

    def call(self, *args, timeout=120):
        command = ["gcloud", *args, f"--project={PROJECT}", "--format=json", "--quiet"]
        self.sequence += 1
        prefix = self.output / f"{self.sequence:03d}" if self.output else None
        if prefix:
            prefix.with_suffix(".command.json").write_text(json.dumps(command))
        # Timeout/transport errors are ambiguous: never retry creation elsewhere on them.
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        if prefix:
            prefix.with_suffix(".stdout").write_text(result.stdout)
            prefix.with_suffix(".stderr").write_text(result.stderr)
        if result.returncode:
            raise CommandError(result)
        return json.loads(result.stdout) if result.stdout.strip() else None


def candidates(quotes, regions, accelerators, machines, hours, budget, spent, reserve):
    supported = ({r["zone"].rsplit("/", 1)[-1] for r in accelerators if r["name"] == GPU}
                 & {r["zone"].rsplit("/", 1)[-1] for r in machines if r["name"] == MACHINE})
    groups, skipped = [], {}
    for region in dict.fromkeys(regions):
        rate = positive(quotes[region]["hourly_usd"])
        if not rate:
            raise ValueError(f"Missing positive rate for {region}")
        if spent + reserve + hours * rate > budget:
            skipped[region] = "above total allowance including reserve"
            continue
        zones = sorted(z for z in supported if z.rsplit("-", 1)[0] == region)
        if not zones:
            skipped[region] = "no zone advertises both this GPU and machine"
        groups.append([{"region": region, "zone": z, "hourly_usd": rate} for z in zones])
    # JUDGEMENT: Region order — Codex, 2026-11-02: spread attempts across the supplied
    # regions before second zones. Exhausting one region first may find different capacity.
    ordered = [group[i] for i in range(max(map(len, groups), default=0))
               for group in groups if i < len(group)]
    return ordered, skipped


def plan(args, cloud, now):
    deadline = timestamp(args.deadline)
    if not timedelta(minutes=5, seconds=30) < deadline - now <= timedelta(hours=3):
        raise ValueError("Deadline must be 5m30s to 3h away; it is never extended by retries")
    if not re.fullmatch(r"wh3-[a-z0-9-]{1,35}[a-z0-9]", args.name):
        raise ValueError("Use a unique wh3- name, at most 40 lowercase letters/digits/hyphens")
    if not re.fullmatch(r"windows-server-2022-dc-v[0-9]{8}", args.image):
        raise ValueError("Use a pinned Windows Server 2022 image matching the quote")
    budget, spent, reserve = map(positive, (args.budget_usd, args.spent_usd, args.reserve_usd))
    if not 0 < budget <= 5 or reserve < 1:
        raise ValueError("Current boundary: at most $5 total, with at least $1 reserved")
    quote = json.loads(args.quotes.read_text())
    # JUDGEMENT: Quote age — Codex, 2026-11-02: refuse rates older than one day.
    # A longer validity period avoids refresh work but risks using changed prices.
    if quote["currency"] != "USD" or not timedelta(0) <= now - timestamp(
            quote["quoted_at"]) <= timedelta(days=1):
        raise ValueError("Refresh the USD regional quotes; they must be at most 24 hours old")
    regions = args.regions.split(",") if args.regions else list(quote["regions"])
    unknown = set(regions) - quote["regions"].keys()
    if unknown:
        raise ValueError(f"Quote these regions before adding them: {sorted(unknown)}")
    accelerators = cloud.call("compute", "accelerator-types", "list", f"--filter=name={GPU}")
    machines = cloud.call("compute", "machine-types", "list", f"--filter=name={MACHINE}")
    ordered, skipped = candidates(quote["regions"], regions, accelerators, machines,
                                  (deadline - now).total_seconds() / 3600, budget, spent, reserve)
    return {"project": PROJECT, "name": args.name, "created_at": now.isoformat(),
            "deadline": deadline.isoformat(),
            "native_deadline": (deadline - timedelta(minutes=5)).isoformat(),
            "budget_usd": budget, "spent_usd": spent, "reserve_usd": reserve,
            "image": args.image, "quotes": quote, "candidates": ordered, "skipped": skipped}


def absent(cloud, name):
    """Project-wide check: a leftover in any zone prevents a second billable VM."""
    for resource in ("instances", "disks"):
        rows = cloud.call("compute", resource, "list", f"--filter=name={name}")
        if not isinstance(rows, list):
            raise RuntimeError(f"{name}: {resource} inventory is unknown; stop retries")
        if rows:
            raise RuntimeError(f"{name}: {resource} still exist; stop and inspect cleanup")


def arm(cloud, session, zone, directory):
    workflow = session["name"] + "-cleanup"
    source = CLEANUP.read_text()
    for key, value in {"NAME": session["name"], "ZONE": zone,
                       "DEADLINE": session["deadline"]}.items():
        source = source.replace("__" + key + "__", json.dumps(value))
    path = directory / "cleanup.yaml"
    path.write_text(source)
    deployed = cloud.call("workflows", "deploy", workflow, f"--location={LOCATION}",
                         f"--source={path}", "--call-log-level=log-errors-only",
                         f"--service-account=wh3-cleanup@{PROJECT}.iam.gserviceaccount.com")
    execution = cloud.call("workflows", "execute", workflow, f"--location={LOCATION}")
    (directory / "execution.json").write_text(json.dumps(execution, indent=2))
    for _ in range(5):
        status = cloud.call("workflows", "executions", "describe",
                            execution["name"].rsplit("/", 1)[-1], f"--workflow={workflow}",
                            f"--location={LOCATION}")
        if (status["state"] == "ACTIVE"
                and status["workflowRevisionId"] == deployed["revisionId"]
                and any(s["step"] == "deadline"
                        for s in status.get("status", {}).get("currentSteps", []))):
            return execution
        if status["state"] not in ("QUEUED", "ACTIVE"):
            break
        time.sleep(1)
    raise RuntimeError("Cleanup did not reach its deadline wait; no VM created")


def create_args(session, zone):
    return ["compute", "instances", "create", session["name"], f"--zone={zone}",
            f"--machine-type={MACHINE}", f"--accelerator=type={GPU},count=1",
            "--maintenance-policy=TERMINATE", "--provisioning-model=STANDARD",
            "--no-restart-on-failure", "--termination-time=" + session["native_deadline"],
            "--instance-termination-action=DELETE", "--image-project=windows-cloud",
            "--image=" + session["image"], "--boot-disk-size=250GB",
            "--boot-disk-type=pd-balanced", "--boot-disk-auto-delete",
            "--no-enable-display-device", "--no-deletion-protection", "--tags=wh3-worker",
            f"--service-account=wh3-vm@{PROJECT}.iam.gserviceaccount.com",
            "--scopes=cloud-platform", "--metadata=enable-windows-ssh=TRUE",
            f"--metadata-from-file=sysprep-specialize-script-ps1={BOOTSTRAP}",
            "--labels=purpose=wh3-compatibility"]


def provision(session, cloud, output, now=lambda: datetime.now(UTC)):
    output.mkdir(parents=True, exist_ok=False)  # Never erase/restart an attempted session.
    cloud.output = output
    state = {"plan": session, "attempts": [], "status": "starting"}

    def save():
        (output / "state.json").write_text(json.dumps(state, indent=2) + "\n")

    save()
    try:
        if not session["candidates"]:
            state["status"] = "exhausted"
            save()
            return state
        absent(cloud, session["name"])
        workflows = cloud.call("workflows", "list", f"--location={LOCATION}",
                               f"--filter=name:{session['name']}-cleanup")
        if not isinstance(workflows, list):
            raise RuntimeError("Cleanup workflow inventory is unknown; stop retries")
        if workflows:
            raise RuntimeError("Cleanup workflow already exists; use a new session name")
        # Support resources are prepared separately; missing prerequisites fail before spending.
        for name in ("wh3-cleanup", "wh3-vm"):
            cloud.call("iam", "service-accounts", "describe",
                       f"{name}@{PROJECT}.iam.gserviceaccount.com")
        cloud.call("compute", "firewall-rules", "describe", "wh3-allow-iap")
        for candidate in session["candidates"]:
            if now() + timedelta(seconds=30) >= timestamp(session["native_deadline"]):
                raise RuntimeError("Original deadline reached; no further attempt")
            zone = candidate["zone"]
            attempt = {**candidate, "status": "arming"}
            state["attempts"].append(attempt)
            save()
            directory = output / zone
            directory.mkdir()
            execution = arm(cloud, session, zone, directory)
            attempt["execution"] = execution["name"]
            absent(cloud, session["name"])
            if now() + timedelta(seconds=30) >= timestamp(session["native_deadline"]):
                raise RuntimeError("Original deadline reached during cleanup arming")
            attempt["status"] = "creating"
            save()
            try:
                vm = cloud.call(*create_args(session, zone), timeout=240)
            except CommandError as error:
                attempt["error"] = str(error)
                if not STOCKOUT.search(str(error)):
                    raise
                # Like SkyPilot, never continue on uncertain cleanup. Keep the remote backup.
                absent(cloud, session["name"])
                cloud.call("workflows", "executions", "cancel",
                           execution["name"].rsplit("/", 1)[-1],
                           f"--workflow={session['name']}-cleanup", f"--location={LOCATION}")
                attempt["status"] = "stockout"
                save()
                continue
            if (len(vm) != 1 or vm[0]["name"] != session["name"]
                    or vm[0]["zone"].rsplit("/", 1)[-1] != zone
                    or not all(d["autoDelete"] for d in vm[0]["disks"])
                    or vm[0]["scheduling"]["instanceTerminationAction"] != "DELETE"
                    or timestamp(vm[0]["scheduling"]["terminationTime"])
                    != timestamp(session["native_deadline"])):
                raise RuntimeError("Created VM differs from its deletion plan; inspect it now")
            attempt["status"] = "created"
            state.update(status="created", selected=zone)
            save()
            return state
        state["status"] = "exhausted"
        save()
        return state
    except (Exception, KeyboardInterrupt) as error:
        state.update(status="stopped", error=str(error))
        save()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="unique wh3- session name")
    parser.add_argument("--deadline", required=True, help="absolute ISO time, including timezone")
    parser.add_argument("--regions", help="ordered comma-separated regions; default: all quotes")
    parser.add_argument("--quotes", type=Path, default=QUOTES)
    parser.add_argument("--budget-usd", type=float, default=5)
    parser.add_argument("--spent-usd", type=float, required=True,
                        help="earlier cloud spend/allowance")
    # JUDGEMENT: Reserve — Codex, 2026-11-02: at least $1 for tax, traffic, teardown and
    # failed-attempt storage. Smaller reserves admit dearer regions; neither is a hard cap.
    parser.add_argument("--reserve-usd", type=float, default=1)
    parser.add_argument("--image", default="windows-server-2022-dc-v20261026")
    parser.add_argument("--output", type=Path, help="new evidence directory under runs/")
    parser.add_argument("--create", action="store_true", help="provision; default only previews")
    args = parser.parse_args()
    if args.create and (not args.output or not args.output.resolve().is_relative_to(ROOT / "runs")):
        parser.error("--create needs a new --output under runs/")
    session = plan(args, GCloud(), datetime.now(UTC))
    if not args.create:
        print(json.dumps(session, indent=2))
        return 0
    state = provision(session, GCloud(), args.output)
    print(json.dumps({"status": state["status"], "selected": state.get("selected"),
                      "evidence": str(args.output)}))
    return 0 if state["status"] == "created" else 1


if __name__ == "__main__":
    raise SystemExit(main())
