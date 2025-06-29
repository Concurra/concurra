import time
import pytest
import logging
from concurra.core import TaskRunner

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


def dummy_success(x):
    time.sleep(x)
    return x * 2

def dummy_failure(x):
    raise ValueError("Intentional failure")

def test_successful_task_execution():
    runner = TaskRunner(max_concurrency=2, logger=LOGGER)
    runner.add_task(dummy_success, 3, label="task1")
    runner.add_task(dummy_success, 5, label="task2")
    results = runner.run()

    assert results["task1"]["result"] == 6
    assert results["task1"]["has_failed"] is False
    assert results["task2"]["result"] == 10
    assert results["task2"]["has_failed"] is False

def test_task_failure_handling():
    runner = TaskRunner(max_concurrency=1, log_errors=True, logger=LOGGER)
    runner.add_task(dummy_failure, 3, label="fail_task")
    results = runner.run(verify=False)

    assert "fail_task" in results
    assert results["fail_task"]["has_failed"] is True
    assert "Intentional failure" in results["fail_task"]["error"]

def test_fast_fail_behavior():
    runner = TaskRunner(fast_fail=True, logger=LOGGER)
    runner.add_task(dummy_failure, 1, label="fail_task")
    runner.add_task(dummy_success, 2, label="should_not_run")

    results = runner.run(verify=False)

    assert results["fail_task"]["has_failed"] is True
    assert "should_not_run" in results
    assert results["should_not_run"]["status"] in ["Terminated", "Failed"]

def test_abort_execution():
    runner = TaskRunner(logger=LOGGER)
    runner.add_task(dummy_success, 10, label="long_task")
    runner.execute_in_background()
    time.sleep(0.2)
    results = runner.abort()

    assert "long_task" in results
    assert results["long_task"]["status"] in ["Terminated", "Failed"]

def test_background_execution_and_results():
    runner = TaskRunner(logger=LOGGER)
    runner.add_task(dummy_success, 4, label="bg_task1")
    runner.add_task(dummy_success, 3, label="bg_task2")
    runner.execute_in_background()
    results = runner.get_background_results()
    assert results["bg_task1"]["result"] == 8
    assert results["bg_task2"]["result"] == 6
    assert results["bg_task1"]["has_failed"] is False
    assert results["bg_task2"]["has_failed"] is False

def test_multiprocessing_success():
    runner = TaskRunner(max_concurrency=2, use_multiprocessing=True, logger=LOGGER)

    runner.add_task(dummy_success, 2, label="mp_task1")
    runner.add_task(dummy_success, 3, label="mp_task2")
    results = runner.run()

    assert results["mp_task1"]["result"] == 4
    assert results["mp_task2"]["result"] == 6
    assert results["mp_task1"]["has_failed"] is False
    assert results["mp_task2"]["has_failed"] is False

def test_fail_fast_with_multiprocessing():
    runner = TaskRunner(
        max_concurrency=2,
        use_multiprocessing=True,
        fast_fail=True,
        logger=LOGGER
    )

    runner.add_task(dummy_failure, 1, label="fail_fast_mp")
    runner.add_task(dummy_success, 3, label="should_not_run_mp")

    results = runner.run(verify=False)

    assert results["fail_fast_mp"]["has_failed"] is True
    assert "should_not_run_mp" in results
    assert results["should_not_run_mp"]["status"] in ["Terminated", "Failed"]

def test_task_timeout():
    runner = TaskRunner(timeout=5, logger=LOGGER)
    runner.add_task(dummy_success, 1, label="fast_task") # Timeout in seconds
    runner.add_task(dummy_success, 10, label="slow_task")

    results = runner.run(verify=False)

    assert "slow_task" in results
    assert results["fast_task"]["has_failed"] is False
    assert results["fast_task"]["result"] == 2
    assert results["slow_task"]["status"] in ["TimedOut", "Failed", "Terminated"]
    assert results["slow_task"]["has_failed"] is True

def test_no_tasks():
    runner = TaskRunner(logger=LOGGER)
    results = runner.run()
    assert results == {}

def test_duplicate_labels():
    runner = TaskRunner(logger=LOGGER)
    runner.add_task(dummy_success, 1, label="dup")
    with pytest.raises(ValueError):
        runner.add_task(dummy_success, 2, label="dup")

def test_invalid_function_addition():
    runner = TaskRunner(logger=LOGGER)
    with pytest.raises(TypeError):
        runner.add_task("not_a_function", label="invalid")

def test_run_after_background():
    runner = TaskRunner(logger=LOGGER)
    runner.add_task(dummy_success, 1, label="bg")
    runner.execute_in_background()
    with pytest.raises(RuntimeError):
        runner.run()

def test_task_without_label():
    runner = TaskRunner(logger=LOGGER)
    runner.add_task(dummy_success, 2)
    results = runner.run()

    assert results[0]["result"] == 4

def test_multiple_fast_fail_tasks():
    runner = TaskRunner(fast_fail=True, logger=LOGGER)
    runner.add_task(dummy_failure, 1, label="fail_task1")
    runner.add_task(dummy_failure, 2, label="fail_task2")
    runner.add_task(dummy_success, 3, label="success_task")

    results = runner.run(verify=False)

    assert results["fail_task1"]["has_failed"] is True
    assert results["fail_task2"]["has_failed"] is True
    assert results["success_task"]["status"] in ["Terminated", "Failed"]

def test_instance_reset():
    runner1 = TaskRunner(logger=LOGGER)
    runner1.add_task(dummy_success, 1, label="task1")
    runner1.run()

    # Create a new instance and add tasks
    runner2 = TaskRunner(logger=LOGGER)
    runner2.add_task(dummy_success, 2, label="task2")
    results = runner2.run()

    assert "task2" in results
    assert results["task2"]["result"] == 4

def test_abort_task_with_results():
    runner = TaskRunner(logger=LOGGER)
    runner.add_task(dummy_success, 10, label="long_task")
    runner.execute_in_background()

    time.sleep(2)
    results = runner.abort()

    assert "long_task" in results
    assert results["long_task"]["status"] in ["Terminated", "Failed"]
    assert results["long_task"]["has_failed"] is True

def test_add_work_method():
    runner = TaskRunner(logger=LOGGER)

    workload = [
        (dummy_success, (1,), {}, "task1"),
        (dummy_success, (2,), {}, "task2"),
        (dummy_success, (1,))  # Minimal valid input
    ]

    runner.add_work(workload)
    results = runner.run()

    assert results["task1"]["result"] == 2
    assert results["task2"]["result"] == 4
    assert results[2]["result"] == 2  # dummy_success(None) → None*2 → error, so use safe input

def test_runner_len():
    runner = TaskRunner(logger=LOGGER)
    runner.add_task(dummy_success, 1)
    runner.add_task(dummy_success, 2)

    assert len(runner) == 2

def test_get_active_runner_count():
    runner = TaskRunner(logger=LOGGER)
    runner.add_task(dummy_success, 3, label="active_task")
    runner.add_task(dummy_success, 4, label="active_task2")
    runner.execute_in_background()

    time.sleep(0.5)  # Give time to start the task
    active_count = runner.get_active_runner_count()

    assert active_count >= 1

    # Wait for completion to ensure count drops to 0
    time.sleep(6)
    assert runner.get_active_runner_count() == 0

