"""Scripted members, a controlled worker pool and inputs shared by the team tests."""
from concurrent.futures import Future

from wh3_fixtures import bridge_observation

from twwarhammer3.battle import team


def state(seq=1, time_ms=10000, **changes):
    observation = bridge_observation(seq, time_ms, **changes)
    observation["friendly"] = [
        {"id": "f2", "type": team.SWORD, "x": 0, "z": 0, "bearing": 0, "men": 100,
         "state": ["idle"], "target": "hidden", "target_dead": True},
        {"id": "f1", "type": team.KNIGHT, "x": 20, "z": 0, "bearing": 0, "men": 60,
         "state": ["idle"], "target": "e1"},
    ]
    observation["terrain"] = {"rows": ["...", "..."], "cell_m": 32, "x0": 0, "z0": 0,
                              "bounds": {"min_x": -50, "max_x": 50, "private": 99}}
    return observation


def move(unit):
    return {"unit": unit, "type": "move", "x": 10, "z": 20, "run": True}


class Script:
    def __init__(self, orders=None):
        self.orders = orders
        self.inputs, self.feedback = [], []
        self.closed = False

    def decide(self, observation):
        self.inputs.append(observation)
        return self.orders if self.orders is not None else [move(observation["friendly"][0]["id"])]

    def metadata(self):
        return {"type": "test_script"}

    def acknowledge(self, ack, latency):
        self.feedback.append((ack, latency))

    def close(self):
        self.closed = True


class Workers:
    """Complete chosen real member calls without relying on thread timing."""
    def __init__(self):
        self.tasks = []

    def submit(self, fn, *args):
        future = Future()
        self.tasks.append((future, fn, args))
        return future

    def finish(self, index):
        future, fn, args = self.tasks[index]
        try:
            future.set_result(fn(*args))
        except Exception as exc:
            future.set_exception(exc)

    def shutdown(self, wait):
        for index, (future, _, _) in enumerate(self.tasks):
            if not future.done():
                self.finish(index)


def make_team(a=None, b=None, **kwargs):
    a, b = a or Script(), b or Script()
    workers = Workers()
    policy = team.TeamPolicy({"infantry": (team.SWORD, a), "cavalry": (team.KNIGHT, b)},
                             executor=workers, **kwargs)
    return policy, workers, a, b


def ack(policy, *, applied=13400, results=None):
    policy.acknowledge({"request": "r1", "applied_ms": applied,
                        "results": results if results is not None else []},
                       {"delay_ms": 400, "think_s": .001, "roundtrip_s": .5})
