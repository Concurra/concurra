import pytest
import logging
import time
from time import sleep
from concurra import TaskRunner
from datetime import datetime

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
# Optional: Add a handler to output logs to the console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
# Set up a formatter (optional)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
# Add the handler to the logger
LOGGER.addHandler(console_handler)


def test_single_dependency():
    order = []

    def task_a():
        order.append("A")

    def task_b():
        order.append("B")

    runner = TaskRunner(max_concurrency=2)
    runner.add_task(task_a, label="A")
    runner.add_task(task_b, label="B", depends_on={"A"})
    runner.run()

    assert order == ["A", "B"]

def test_multiple_dependencies():
    order = []

    def task_a(): order.append("A")
    def task_b(): order.append("B")
    def task_c(): order.append("C")

    runner = TaskRunner(max_concurrency=3)
    runner.add_task(task_a, label="A")
    runner.add_task(task_b, label="B")
    runner.add_task(task_c, label="C", depends_on={"A", "B"})
    runner.run()

    assert "C" in order
    assert order.index("C") > order.index("A")
    assert order.index("C") > order.index("B")

def test_failed_dependency_skips_dependent():
    def task_fail():
        raise RuntimeError("fail")

    def task_should_skip():
        pytest.fail("This should not be executed if dependency fails.")

    runner = TaskRunner()
    runner.add_task(task_fail, label="fail_task")
    runner.add_task(task_should_skip, label="dependent", depends_on={"fail_task"})
    runner.run(verify=False)
    assert "fail_task" in runner._failed_tasks
    assert "dependent" in runner._terminated_tasks  # dependent should be skipped

def test_parallel_execution_of_independents():
    executed = []

    def task(x):
        sleep(0.1)
        executed.append(x)

    runner = TaskRunner(max_concurrency=3)
    for i in range(3):
        runner.add_task(task, i, label=f"T{i}")
    runner.run()

    assert set(executed) == {0, 1, 2}

def test_chained_dependencies():
    order = []

    def a(): order.append("A")
    def b(): order.append("B")
    def c(): order.append("C")

    runner = TaskRunner()
    runner.add_task(a, label="A")
    runner.add_task(b, label="B", depends_on={"A"})
    runner.add_task(c, label="C", depends_on={"B"})
    runner.run()

    assert order == ["A", "B", "C"]

def dummy(): pass

def test_direct_circular_dependency():
    runner = TaskRunner()
    with pytest.raises(ValueError, match="cannot depend on itself"):
        runner.add_task(dummy, label="A", depends_on={"A"})

def test_two_way_circular_dependency():
    runner = TaskRunner()
    runner.add_task(dummy, label="A", depends_on={"B"})
    with pytest.raises(ValueError, match="Circular dependency detected"):
        runner.add_task(dummy, label="B", depends_on={"A"})

def test_concurrency_and_dependency_timing():
    def make_task(label, sleep_time=0):
        def task():
            time.sleep(sleep_time)
        return task

    runner = TaskRunner(max_concurrency=4)

    # Tasks 2 and 3 are slow
    runner.add_task(make_task("T0"), label="T0")
    runner.add_task(make_task("T1"), label="T1")
    runner.add_task(make_task("T2", sleep_time=4), label="T2")
    runner.add_task(make_task("T3", sleep_time=3), label="T3")
    runner.add_task(make_task("T4"), label="T4", depends_on={"T2", "T3"})  # Dependent
    runner.add_task(make_task("T5"), label="T5", sleep_time=5)  # Independent
    runner.add_task(make_task("T6", sleep_time=3), label="T6")
    runner.add_task(make_task("T7"), label="T7",sleep_time=2)
    runner.add_task(make_task("T8"), label="T8",sleep_time=1)
    runner.add_task(make_task("T9"), label="T9")

    results = runner.run()

    # Parse start times
    def start(label):
        return time.strptime(results[label]["start_time"], "%Y-%m-%d %H:%M:%S")

    # Ensure T4 starts after both T2 and T3 are done
    t4_start = start("T4")
    t2_start = time.strptime(results["T2"]["start_time"], "%Y-%m-%d %H:%M:%S")
    t3_start = time.strptime(results["T3"]["start_time"], "%Y-%m-%d %H:%M:%S")

    assert t4_start > t2_start
    assert t4_start > t3_start

    # Ensure T5 (independent) runs earlier than T4
    t5_start = start("T5")
    assert t5_start < t4_start

def test_concurrency_never_exceeds_limit():
    events = []

    def make_task(label, sleep_time=1):
        def task():
            events.append(("start", label, datetime.now()))
            time.sleep(sleep_time)
            events.append(("end", label, datetime.now()))
        return task

    max_concurrency = 4
    runner = TaskRunner(max_concurrency=max_concurrency, logger=LOGGER)

    # Add 10 dummy tasks
    for i in range(10):
        runner.add_task(make_task(f"T{i}"), label=f"T{i}")

    runner.run()

    # Analyze concurrent execution based on start/end times
    running = []
    timeline = sorted(events, key=lambda x: x[2])  # sort by timestamp

    max_running = 0

    for event_type, label, ts in timeline:
        if event_type == "start":
            running.append(label)
        elif event_type == "end":
            running.remove(label)

        if len(running) > max_running:
            max_running = len(running)

    assert max_running <= max_concurrency
