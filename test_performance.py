"""Registration stress test; set CONCURRA_REGISTRATION_BUDGET_SECONDS for a timed benchmark."""

import os
import time


from concurra import TaskRunner

def dummy_success(x):
    pass

def test_add_1m_tasks(monkeypatch, record_property):

    def unexpected_graph_walk(*args):
        raise AssertionError("Independent task registration must not traverse the dependency graph")

    runner = TaskRunner(max_concurrency=2)
    monkeypatch.setattr(runner, "_find_cycle_from_new_task", unexpected_graph_walk)
    start = time.perf_counter()

    for _ in range(1_000_000):
        runner.add_task(dummy_success)

    elapsed = time.perf_counter() - start
    record_property("registration_seconds", elapsed)
    assert len(runner) == len(runner.tasks) == len(runner.results_registry) == 1_000_000
    assert runner.tasks[0].label == 0
    assert runner.tasks[-1].label == 999_999

    # Hosted CI hardware varies. Enforce a wall-clock budget only on an
    # explicitly configured benchmark machine, retaining the full stress test.
    budget = os.environ.get("CONCURRA_REGISTRATION_BUDGET_SECONDS")
    if budget is not None:
        assert elapsed < float(budget)
