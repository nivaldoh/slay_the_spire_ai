"""Cloud allowance and retry contracts; fake gcloud, never creates cloud resources."""

import importlib.util
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location(
    "wh3_gcp", Path(__file__).resolve().parents[2] / "scripts/wh3_gcp.py")
gcp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gcp)
NOW = datetime(2026, 11, 3, tzinfo=UTC)
CAPACITY = "ERROR: create failed\n---\ncode: ZONE_RESOURCE_POOL_EXHAUSTED_WITH_DETAILS\n"


class Cloud:
    """Fake provider state: a failed insert may leave a disk, just like a partial create."""

    def __init__(self, outcomes=(), leftover=None, arm_state="ACTIVE"):
        self.outcomes = iter(outcomes)
        self.calls = []
        self.leftover = leftover
        self.arm_state = arm_state
        self.sources = []
        self.output = None

    def call(self, *args, **kwargs):
        self.calls.append(args)
        if args[:3] in (("compute", "instances", "list"), ("compute", "disks", "list")):
            return [{"name": "wh3-test"}] if self.leftover == args[1] else []
        if args[:2] == ("workflows", "deploy"):
            self.sources.append(Path(flag(args, "--source")).read_text())
            return {"revisionId": "revision-1"}
        if args[:2] == ("workflows", "list"):
            return []
        if args[:2] == ("workflows", "execute"):
            return {"name": "projects/p/locations/l/workflows/w/executions/execution-1"}
        if args[:3] == ("workflows", "executions", "describe"):
            return {"state": self.arm_state, "workflowRevisionId": "revision-1",
                    "status": {"currentSteps": [{"step": "deadline"}]}}
        if args[:3] == ("compute", "instances", "create"):
            outcome = next(self.outcomes)
            if outcome == "timeout":
                raise subprocess.TimeoutExpired(args, 240)
            if outcome in ("stockout", "leak", "permission", "quota"):
                if outcome == "leak":
                    self.leftover = "disks"
                error = CAPACITY if outcome in ("stockout", "leak") else f"code: {outcome}\n"
                raise gcp.CommandError(subprocess.CompletedProcess(args, 1, "", error))
            return [{"name": "wh3-test", "zone": "zones/" + flag(args, "--zone"),
                     "disks": [{"autoDelete": outcome != "bad_disk"}], "scheduling": {
                         "instanceTerminationAction": "DELETE",
                         "terminationTime": flag(args, "--termination-time")}}]
        return {}


def flag(args, name):
    return next(x.split("=", 1)[1] for x in args if x.startswith(name + "="))


def session():
    return {"name": "wh3-test", "deadline": "2026-11-03T03:00:00+00:00",
            "native_deadline": "2026-11-03T02:55:00+00:00",
            "image": "windows-server-2022-dc-v20261026",
            "candidates": [{"zone": "us-east1-b"}, {"zone": "europe-west4-a"},
                           {"zone": "asia-east1-a"}]}


def creates(cloud):
    return [c for c in cloud.calls if c[:3] == ("compute", "instances", "create")]


def cancelled(cloud):
    return [c for c in cloud.calls if c[:3] == ("workflows", "executions", "cancel")]


def test_stockout_moves_region_with_same_deadline_then_stops_at_success(tmp_path):
    cloud = Cloud(["stockout", "success", "success"])
    state = gcp.provision(session(), cloud, tmp_path / "session", now=lambda: NOW)
    assert state["status"] == "created" and state["selected"] == "europe-west4-a"
    assert [a["status"] for a in state["attempts"]] == ["stockout", "created"]
    requests = creates(cloud)
    assert [flag(c, "--zone") for c in requests] == ["us-east1-b", "europe-west4-a"]
    for request in requests:
        assert flag(request, "--termination-time") == "2026-11-03T02:55:00+00:00"
        assert flag(request, "--machine-type") == "g2-standard-4"
        assert flag(request, "--accelerator") == "type=nvidia-l4-vws,count=1"
        assert "--boot-disk-auto-delete" in request
    assert len(cloud.sources) == 2
    for source, zone in zip(cloud.sources, ["us-east1-b", "europe-west4-a"]):
        assert f'zone: "{zone}"' in source
        assert 'time: "2026-11-03T03:00:00+00:00"' in source
        assert 'instance: "wh3-test"' in source and 'disk: "wh3-test"' in source
        assert source.index("- probe:") < source.index("- deadline:")
        assert "__" not in source
    assert len(cancelled(cloud)) == 1  # successful host's backup stays armed
    for i, call in enumerate(cloud.calls):
        if call in requests:
            assert any(c[:3] == ("workflows", "executions", "describe")
                       for c in cloud.calls[:i])


@pytest.mark.parametrize("failure", ["permission", "quota", "timeout", "leak", "bad_disk"])
def test_ambiguous_or_noncapacity_failure_never_creates_second_host(tmp_path, failure):
    cloud = Cloud([failure, "success"])
    with pytest.raises((RuntimeError, subprocess.TimeoutExpired)):
        gcp.provision(session(), cloud, tmp_path / "session", now=lambda: NOW)
    assert len(creates(cloud)) == 1 and not cancelled(cloud)
    state = json.loads((tmp_path / "session/state.json").read_text())
    assert state["status"] == "stopped"


@pytest.mark.parametrize("leftover", ["instances", "disks"])
def test_preexisting_target_cannot_be_adopted_or_deleted(tmp_path, leftover):
    cloud = Cloud(["success"], leftover=leftover)
    with pytest.raises(RuntimeError, match="still exist"):
        gcp.provision(session(), cloud, tmp_path / "session", now=lambda: NOW)
    assert not creates(cloud) and not cloud.sources


@pytest.mark.parametrize("inventory", [None, {}, False, 0, ""])
def test_unknown_inventory_is_not_proof_of_absence(tmp_path, inventory):
    class UnknownInventory(Cloud):
        def call(self, *args, **kwargs):
            if args[:3] == ("compute", "disks", "list"):
                return inventory
            return super().call(*args, **kwargs)

    cloud = UnknownInventory(["success"])
    with pytest.raises(RuntimeError, match="inventory is unknown"):
        gcp.provision(session(), cloud, tmp_path / "session", now=lambda: NOW)
    assert not creates(cloud) and not cloud.sources


def test_all_stockouts_exhaust_candidates_and_existing_output_cannot_restart(tmp_path):
    cloud = Cloud(["stockout"] * 3)
    output = tmp_path / "session"
    state = gcp.provision(session(), cloud, output, now=lambda: NOW)
    assert state["status"] == "exhausted" and len(cancelled(cloud)) == 3
    count = len(cloud.calls)
    with pytest.raises(FileExistsError):
        gcp.provision(session(), cloud, output, now=lambda: NOW)
    assert len(cloud.calls) == count


def test_expiry_during_arming_never_sends_insert(tmp_path):
    clock = iter([NOW, NOW + timedelta(hours=3)])
    cloud = Cloud(["success"])
    with pytest.raises(RuntimeError, match="deadline reached"):
        gcp.provision(session(), cloud, tmp_path / "session", now=lambda: next(clock))
    assert not creates(cloud) and not cancelled(cloud)


def test_failed_cleanup_execution_cannot_be_mistaken_for_cli_success(tmp_path):
    cloud = Cloud(["success"], arm_state="FAILED")
    with pytest.raises(RuntimeError, match="Cleanup did not reach"):
        gcp.provision(session(), cloud, tmp_path / "session", now=lambda: NOW)
    assert not creates(cloud)


def test_no_affordable_candidate_needs_no_cloud_mutations(tmp_path):
    cloud = Cloud()
    data = session()
    data["candidates"] = []
    result = gcp.provision(data, cloud, tmp_path / "session", now=lambda: NOW)
    assert result["status"] == "exhausted" and cloud.calls == []


def test_only_quoted_affordable_supported_zones_are_interleaved():
    zones = ["us-east1-b", "us-east1-c", "europe-west4-a", "europe-west4-b",
             "asia-east1-a", "asia-east1-b"]
    gpu = [{"zone": "zones/" + z, "name": "nvidia-l4-vws"} for z in zones]
    machines = [{"zone": "zones/" + z, "name": "g2-standard-4"} for z in zones[:-1]]
    quotes = {"us-east1": {"hourly_usd": 1.1}, "europe-west4": {"hourly_usd": 1.2},
              "asia-east1": {"hourly_usd": 1.5}, "absent": {"hourly_usd": 1}}
    options, skipped = gcp.candidates(quotes, list(quotes), gpu, machines, 3, 5, .03, 1)
    assert [x["zone"] for x in options] == ["us-east1-b", "europe-west4-a",
                                           "us-east1-c", "europe-west4-b"]
    assert set(skipped) == {"asia-east1", "absent"}
    options, _ = gcp.candidates(quotes, ["asia-east1"], gpu, machines, 1, 5, .03, 1)
    assert [x["zone"] for x in options] == ["asia-east1-a"]  # GPU-only zone excluded


def arguments(tmp_path):
    quotes = tmp_path / "quote.json"
    quotes.write_text(json.dumps({"currency": "USD", "quoted_at": NOW.isoformat(),
                                 "regions": {"us-east1": {"hourly_usd": 1.1}}}))
    return SimpleNamespace(deadline=(NOW + timedelta(hours=3)).isoformat(), name="wh3-test",
                           budget_usd=5, spent_usd=.03, reserve_usd=1, quotes=quotes,
                           image="windows-server-2022-dc-v20261026", regions=None)


@pytest.mark.parametrize("change", ["late", "naive", "stale", "unquoted", "budget", "nan"])
def test_invalid_spend_plan_stops_before_cloud_calls(tmp_path, change):
    args = arguments(tmp_path)
    if change == "late":
        args.deadline = (NOW + timedelta(hours=4)).isoformat()
    elif change == "naive":
        args.deadline = "2026-11-03T03:00:00"
    elif change == "stale":
        quote = json.loads(args.quotes.read_text())
        quote["quoted_at"] = (NOW - timedelta(days=2)).isoformat()
        args.quotes.write_text(json.dumps(quote))
    elif change == "unquoted":
        args.regions = "unpriced-region"
    elif change == "budget":
        args.budget_usd = 6
    else:
        args.spent_usd = float("nan")
    cloud = Cloud()
    with pytest.raises(ValueError):
        gcp.plan(args, cloud, NOW)
    assert cloud.calls == []


def test_gcloud_always_selects_project_and_retains_failure_evidence(tmp_path, monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 1, "", CAPACITY)

    monkeypatch.setattr(gcp.subprocess, "run", run)
    with pytest.raises(gcp.CommandError):
        gcp.GCloud(tmp_path).call("compute", "instances", "create", "wh3-test")
    assert "--project=wh3-benchmark" in calls[0]
    assert (tmp_path / "001.stderr").read_text() == CAPACITY


def test_capacity_code_inside_unrelated_error_message_is_not_retried():
    message = "Permission denied: message mentions ZONE_RESOURCE_POOL_EXHAUSTED"
    assert not gcp.STOCKOUT.search(message)
