import time
import sys
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

def echo_kwargs(**kwargs):
    return kwargs

def task_retries_kwarg(task_retries):
    return task_retries

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

def test_task_retries_succeeds_after_transient_failure():
    attempts = {"count": 0}

    def flaky_task():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError(f"temporary failure {attempts['count']}")
        return "ok"

    runner = TaskRunner(task_retries=2, progress_stats=False, logger=LOGGER)
    runner.add_task(flaky_task, label="flaky")
    results = runner.run()

    assert results["flaky"]["status"] == "Successful"
    assert results["flaky"]["result"] == "ok"
    assert results["flaky"]["attempts"] == 3
    assert results["flaky"]["task_retries"] == 2
    assert results["flaky"]["retried"] is True
    assert len(results["flaky"]["retry_errors"]) == 2

def test_task_retries_fails_after_exhausting_attempts():
    attempts = {"count": 0}

    def always_fails():
        attempts["count"] += 1
        raise RuntimeError(f"failure {attempts['count']}")

    runner = TaskRunner(task_retries=2, progress_stats=False, logger=LOGGER)
    runner.add_task(always_fails, label="always_fails")
    results = runner.run(verify=False)

    assert results["always_fails"]["status"] == "Failed"
    assert results["always_fails"]["has_failed"] is True
    assert results["always_fails"]["attempts"] == 3
    assert results["always_fails"]["task_retries"] == 2
    assert results["always_fails"]["retried"] is True
    assert len(results["always_fails"]["retry_errors"]) == 3
    assert "failure 3" in results["always_fails"]["error"]

def test_per_task_retries_override_runner_default():
    attempts = {"count": 0}

    def succeeds_on_second_attempt():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("first attempt failed")
        return attempts["count"]

    runner = TaskRunner(task_retries=0, progress_stats=False, logger=LOGGER)
    runner.add_task(succeeds_on_second_attempt, label="override", task_retries=1)
    results = runner.run()

    assert results["override"]["status"] == "Successful"
    assert results["override"]["result"] == 2
    assert results["override"]["attempts"] == 2
    assert results["override"]["task_retries"] == 1

def test_task_retries_are_not_applied_to_timeouts():
    runner = TaskRunner(timeout=0.1, task_retries=2, progress_stats=False, logger=LOGGER)
    runner.add_task(dummy_success, 0.3, label="slow")
    results = runner.run(verify=False)

    assert results["slow"]["status"] == "Terminated"
    assert results["slow"]["has_failed"] is True
    assert results["slow"]["attempts"] == 1
    assert results["slow"]["task_retries"] == 2
    assert results["slow"]["retried"] is False
    assert results["slow"]["retry_errors"] == []

def test_task_retries_must_be_non_negative_integer():
    with pytest.raises(ValueError):
        TaskRunner(task_retries=-1)

    with pytest.raises(TypeError):
        TaskRunner(task_retries=True)

    runner = TaskRunner(progress_stats=False, logger=LOGGER)
    with pytest.raises(TypeError):
        runner.add_task(dummy_success, 0, label="bad", task_retries=1.5)

def test_add_function_allows_task_kwarg_named_task_retries():
    runner = TaskRunner(progress_stats=False, logger=LOGGER)
    runner.add_function(task_retries_kwarg, kwargs={"task_retries": "payload"}, key="task")

    results = runner.run()

    assert results["task"]["result"] == "payload"
    assert results["task"]["task_retries"] == 0

def test_add_func_forwards_task_retries_to_task():
    runner = TaskRunner(progress_stats=False, logger=LOGGER)
    runner.add_func(task_retries_kwarg, key="task", task_retries="payload")

    results = runner.run()

    assert results["task"]["result"] == "payload"
    assert results["task"]["task_retries"] == 0

def test_multiprocessing_task_retries_record_attempts():
    runner = TaskRunner(
        use_multiprocessing=True,
        task_retries=1,
        progress_stats=False,
        logger=LOGGER
    )
    runner.add_task(dummy_failure, 1, label="fail")

    results = runner.run(verify=False)

    assert results["fail"]["status"] == "Failed"
    assert results["fail"]["attempts"] == 2
    assert results["fail"]["task_retries"] == 1
    assert results["fail"]["retried"] is True
    assert len(results["fail"]["retry_errors"]) == 2

def test_add_command_runs_direct_exec_command():
    runner = TaskRunner(progress_stats=False, logger=LOGGER)
    runner.add_command(
        [sys.executable, "-c", "print('hello from command')"],
        label="cmd"
    )

    results = runner.run()

    assert results["cmd"]["status"] == "Successful"
    assert results["cmd"]["execution_mode"] == "subprocess"
    assert results["cmd"]["result"]["shell"] is False
    assert results["cmd"]["result"]["returncode"] == 0
    assert results["cmd"]["result"]["stdout"].strip() == "hello from command"
    assert results["cmd"]["result"]["stderr"] == ""

def test_add_shell_command_runs_shell_expression():
    runner = TaskRunner(progress_stats=False, logger=LOGGER)
    runner.add_shell_command(
        "printf 'alpha\\nbeta\\n' | grep beta",
        label="shell"
    )

    results = runner.run()

    assert results["shell"]["status"] == "Successful"
    assert results["shell"]["execution_mode"] == "subprocess"
    assert results["shell"]["result"]["shell"] is True
    assert results["shell"]["result"]["returncode"] == 0
    assert results["shell"]["result"]["stdout"].strip() == "beta"

def test_command_validation_rejects_ambiguous_command_forms():
    runner = TaskRunner(progress_stats=False, logger=LOGGER)

    with pytest.raises(TypeError):
        runner.add_command("python tool.py", label="bad_direct")

    with pytest.raises(TypeError):
        runner.add_command([sys.executable, "-c", 1], label="bad_arg")

    with pytest.raises(ValueError):
        runner.add_command([], label="empty")

    with pytest.raises(TypeError):
        runner.add_shell_command([sys.executable, "-c", "print('x')"], label="bad_shell")

    with pytest.raises(ValueError):
        runner.add_shell_command("   ", label="empty_shell")

def test_command_nonzero_exit_fails_with_structured_result():
    runner = TaskRunner(progress_stats=False, logger=LOGGER)
    runner.add_command(
        [sys.executable, "-c", "import sys; print('bad stdout'); print('bad stderr', file=sys.stderr); sys.exit(7)"],
        label="bad"
    )

    results = runner.run(verify=False)

    assert results["bad"]["status"] == "Failed"
    assert results["bad"]["has_failed"] is True
    assert "return code 7" in results["bad"]["error"]
    assert results["bad"]["result"]["returncode"] == 7
    assert results["bad"]["result"]["stdout"].strip() == "bad stdout"
    assert results["bad"]["result"]["stderr"].strip() == "bad stderr"

def test_command_check_false_keeps_nonzero_exit_successful():
    runner = TaskRunner(progress_stats=False, logger=LOGGER)
    runner.add_command(
        [sys.executable, "-c", "import sys; sys.exit(5)"],
        label="nonzero",
        check=False
    )

    results = runner.run()

    assert results["nonzero"]["status"] == "Successful"
    assert results["nonzero"]["has_failed"] is False
    assert results["nonzero"]["result"]["returncode"] == 5

def test_command_and_python_tasks_can_run_together_with_dependencies():
    runner = TaskRunner(max_concurrency=2, progress_stats=False, logger=LOGGER)
    runner.add_task(dummy_success, 0, label="python_first")
    runner.add_command(
        [sys.executable, "-c", "print('command after python')"],
        label="command_after_python",
        depends_on=["python_first"]
    )

    results = runner.run()

    assert results["python_first"]["status"] == "Successful"
    assert results["command_after_python"]["status"] == "Successful"
    assert results["command_after_python"]["result"]["stdout"].strip() == "command after python"

def test_command_uses_subprocess_mode_inside_multiprocessing_runner():
    runner = TaskRunner(
        max_concurrency=2,
        use_multiprocessing=True,
        progress_stats=False,
        logger=LOGGER
    )
    runner.add_task(dummy_success, 0, label="python_process")
    runner.add_command(
        [sys.executable, "-c", "print('command thread')"],
        label="command"
    )

    results = runner.run()

    assert results["python_process"]["status"] == "Successful"
    assert results["python_process"]["execution_mode"] == "process"
    assert results["command"]["status"] == "Successful"
    assert results["command"]["execution_mode"] == "subprocess"
    assert results["command"]["result"]["stdout"].strip() == "command thread"

def test_command_timeout_terminates_subprocess():
    runner = TaskRunner(timeout=0.1, progress_stats=False, logger=LOGGER)
    runner.add_command(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        label="slow_command"
    )

    results = runner.run(verify=False)

    assert results["slow_command"]["status"] == "Terminated"
    assert results["slow_command"]["has_failed"] is True
    assert results["slow_command"]["execution_mode"] == "subprocess"

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

def test_unpicklable_multiprocessing_task_fails_without_blocking_other_tasks():
    runner = TaskRunner(
        max_concurrency=2,
        use_multiprocessing=True,
        progress_stats=False,
        logger=LOGGER
    )

    runner.add_task(lambda: "not picklable", label="unpicklable")
    runner.add_task(dummy_success, 0, label="picklable")
    results = runner.run(verify=False)

    assert results["unpicklable"]["status"] == "Failed"
    assert results["unpicklable"]["has_failed"] is True
    assert "pickle" in results["unpicklable"]["error"].lower()
    assert results["unpicklable"]["execution_mode"] is None
    assert results["unpicklable"]["warning"] == "Task was not picklable and thread fallback is disabled"
    assert results["picklable"]["status"] == "Successful"
    assert results["picklable"]["result"] == 0
    assert results["picklable"]["execution_mode"] == "process"

def test_unpicklable_multiprocessing_task_can_fallback_to_thread():
    runner = TaskRunner(
        max_concurrency=2,
        use_multiprocessing=True,
        fallback_to_thread_on_pickle_error=True,
        progress_stats=False,
        logger=LOGGER
    )

    runner.add_task(lambda: "fallback result", label="fallback")
    runner.add_task(dummy_success, 0, label="process")
    results = runner.run()

    assert results["fallback"]["status"] == "Successful"
    assert results["fallback"]["has_failed"] is False
    assert results["fallback"]["result"] == "fallback result"
    assert results["fallback"]["execution_mode"] == "thread_fallback"
    assert results["fallback"]["warning"] == "Task was not picklable; ran in thread fallback"
    assert results["process"]["status"] == "Successful"
    assert results["process"]["execution_mode"] == "process"

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

def test_timeout_is_applied_per_task_not_entire_run():
    runner = TaskRunner(max_concurrency=1, timeout=0.5, progress_stats=False, logger=LOGGER)
    runner.add_task(dummy_success, 0.3, label="task1")
    runner.add_task(dummy_success, 0.3, label="task2")

    results = runner.run()

    assert results["task1"]["has_failed"] is False
    assert results["task1"]["result"] == 0.6
    assert results["task2"]["has_failed"] is False
    assert results["task2"]["result"] == 0.6

def test_thread_timeout_result_is_not_overwritten_after_task_finishes():
    runner = TaskRunner(timeout=0.1, progress_stats=False, logger=LOGGER)
    runner.add_task(dummy_success, 0.3, label="slow_task")

    results = runner.run(verify=False)
    time.sleep(0.4)

    assert results["slow_task"]["status"] == "Terminated"
    assert results["slow_task"]["has_failed"] is True
    assert runner.results_registry["slow_task"]["status"] == "Terminated"
    assert runner.results_registry["slow_task"]["has_failed"] is True

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

def test_abort_result_is_not_overwritten_after_thread_finishes():
    runner = TaskRunner(progress_stats=False, logger=LOGGER)
    runner.add_task(dummy_success, 0.3, label="long_task")
    runner.execute_in_background()

    time.sleep(0.1)
    results = runner.abort()
    time.sleep(0.4)

    assert results["long_task"]["status"] == "Terminated"
    assert results["long_task"]["has_failed"] is True
    assert runner.results_registry["long_task"]["status"] == "Terminated"
    assert runner.results_registry["long_task"]["has_failed"] is True

def test_add_func_allows_task_kwarg_named_label():
    def task_with_label(label):
        return label

    runner = TaskRunner(progress_stats=False, logger=LOGGER)
    runner.add_func(task_with_label, key="task", label="payload")

    results = runner.run()

    assert results["task"]["result"] == "payload"

def test_add_function_allows_task_kwarg_named_label():
    def task_with_label(label):
        return label

    runner = TaskRunner(progress_stats=False, logger=LOGGER)
    runner.add_function(task_with_label, kwargs={"label": "payload"}, key="task")

    results = runner.run()

    assert results["task"]["result"] == "payload"

def test_add_function_allows_task_kwarg_named_depends_on():
    def task_with_depends_on(depends_on):
        return depends_on

    runner = TaskRunner(progress_stats=False, logger=LOGGER)
    runner.add_function(task_with_depends_on, kwargs={"depends_on": "payload"}, key="task")

    results = runner.run()

    assert results["task"]["result"] == "payload"

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

# --- raise_exception / error_message / verify ---

def test_run_raises_exception_when_task_fails():
    runner = TaskRunner(progress_stats=False, logger=LOGGER)
    runner.add_task(dummy_failure, 1, label="fail")
    with pytest.raises(Exception):
        runner.run(raise_exception=True)

def test_run_raises_with_custom_error_message():
    runner = TaskRunner(progress_stats=False, logger=LOGGER)
    runner.add_task(dummy_failure, 1, label="fail")
    with pytest.raises(Exception, match="my custom failure"):
        runner.run(raise_exception=True, error_message="my custom failure")

def test_run_does_not_raise_on_success():
    runner = TaskRunner(progress_stats=False, logger=LOGGER)
    runner.add_task(dummy_success, 0, label="ok")
    # Should not raise even with raise_exception=True
    results = runner.run(raise_exception=True)
    assert results["ok"]["result"] == 0

def test_verify_raises_while_running():
    runner = TaskRunner(progress_stats=False, logger=LOGGER)
    runner.add_task(dummy_success, 2, label="t")
    runner.execute_in_background()
    time.sleep(0.2)
    with pytest.raises(Exception, match="in progress"):
        runner.verify()
    runner.get_background_results(verify=False)

# --- multiprocessing termination / failure paths ---

def test_multiprocessing_timeout_terminates_process():
    runner = TaskRunner(timeout=0.5, use_multiprocessing=True, progress_stats=False, logger=LOGGER)
    runner.add_task(dummy_success, 5, label="slow")
    results = runner.run(verify=False)

    assert results["slow"]["status"] == "Terminated"
    assert results["slow"]["has_failed"] is True

def test_multiprocessing_abort_terminates_process():
    runner = TaskRunner(use_multiprocessing=True, progress_stats=False, logger=LOGGER)
    runner.add_task(dummy_success, 5, label="long")
    runner.execute_in_background()
    time.sleep(0.5)
    results = runner.abort()

    assert results["long"]["status"] == "Terminated"
    assert results["long"]["has_failed"] is True

def test_multiprocessing_task_failure_is_captured():
    runner = TaskRunner(use_multiprocessing=True, progress_stats=False, logger=LOGGER)
    runner.add_task(dummy_failure, 1, label="fail")
    results = runner.run(verify=False)

    assert results["fail"]["has_failed"] is True
    assert "Intentional failure" in results["fail"]["error"]

# --- fast_fail triggered by timeout ---

def test_fast_fail_triggered_by_timeout():
    runner = TaskRunner(max_concurrency=2, timeout=0.5, fast_fail=True, progress_stats=False, logger=LOGGER)
    runner.add_task(dummy_success, 5, label="slow")
    runner.add_task(dummy_success, 5, label="other")
    results = runner.run(verify=False)

    assert results["slow"]["status"] == "Terminated"
    assert results["slow"]["has_failed"] is True
    assert results["other"]["status"] in ["Terminated", "Failed"]
    assert results["other"]["has_failed"] is True

# --- add_work validation and forwarding ---

def test_add_work_rejects_non_tuple_item():
    runner = TaskRunner(logger=LOGGER)
    with pytest.raises(TypeError):
        runner.add_work([[dummy_success, (1,)]])  # list, not tuple

def test_add_work_rejects_invalid_length():
    runner = TaskRunner(logger=LOGGER)
    with pytest.raises(ValueError):
        runner.add_work([(dummy_success, (1,), {}, "label", "extra")])

def test_add_work_rejects_non_iterable_args():
    runner = TaskRunner(logger=LOGGER)
    with pytest.raises(TypeError):
        runner.add_work([(dummy_success, 5)])

def test_add_work_rejects_non_mapping_kwargs():
    runner = TaskRunner(logger=LOGGER)
    with pytest.raises(TypeError):
        runner.add_work([(dummy_success, (1,), 5)])

def test_add_work_forwards_kwargs():
    runner = TaskRunner(progress_stats=False, logger=LOGGER)
    runner.add_work([(echo_kwargs, (), {"a": 1, "b": 2}, "t")])
    results = runner.run()
    assert results["t"]["result"] == {"a": 1, "b": 2}

# --- wrapper helper semantics ---

def test_add_function_framework_depends_on_orders_execution():
    order = []

    def a():
        order.append("a")

    def b():
        order.append("b")

    runner = TaskRunner(max_concurrency=2, progress_stats=False, logger=LOGGER)
    runner.add_function(a, key="a")
    runner.add_function(b, key="b", depends_on=["a"])
    runner.run()

    assert order == ["a", "b"]

def test_add_func_key_is_reserved_not_forwarded():
    def task(key=None):
        return key

    runner = TaskRunner(progress_stats=False, logger=LOGGER)
    runner.add_func(task, key="the_label")
    results = runner.run()

    assert "the_label" in results
    assert results["the_label"]["result"] is None

def test_add_func_forwards_depends_on_to_task():
    def task(depends_on=None):
        return depends_on

    runner = TaskRunner(progress_stats=False, logger=LOGGER)
    runner.add_func(task, key="t", depends_on="payload")
    results = runner.run()

    assert results["t"]["result"] == "payload"

# --- lifecycle / misc ---

def test_cannot_add_task_after_start():
    runner = TaskRunner(progress_stats=False, logger=LOGGER)
    runner.add_task(dummy_success, 1, label="t")
    runner.execute_in_background()
    with pytest.raises(RuntimeError):
        runner.add_task(dummy_success, 1, label="t2")
    runner.get_background_results(verify=False)

def test_execute_alias_runs_tasks():
    runner = TaskRunner(progress_stats=False, logger=LOGGER)
    runner.add_task(dummy_success, 0, label="t")
    results = runner.execute()
    assert results["t"]["result"] == 0

def test_max_concurrency_below_one_resets_to_one():
    runner = TaskRunner(max_concurrency=-1, progress_stats=False, logger=LOGGER)
    assert runner.max_concurrency == 1

def test_result_schema_and_thread_execution_mode():
    runner = TaskRunner(progress_stats=False, logger=LOGGER)
    runner.add_task(dummy_success, 0, label="t")
    results = runner.run()

    expected_keys = {
        "task_name", "start_time", "end_time", "duration", "duration_seconds",
        "result", "error", "trace", "status", "has_failed", "output",
        "execution_mode", "warning", "attempts", "task_retries", "retried",
        "retry_errors",
    }
    assert set(results["t"].keys()) == expected_keys
    assert results["t"]["execution_mode"] == "thread"
    assert results["t"]["output"] == results["t"]["result"]
    assert results["t"]["warning"] is None
    assert results["t"]["attempts"] == 1
    assert results["t"]["task_retries"] == 0
    assert results["t"]["retried"] is False
    assert results["t"]["retry_errors"] == []

def test_dependent_skipped_when_dependency_times_out():
    runner = TaskRunner(timeout=0.5, max_concurrency=1, progress_stats=False, logger=LOGGER)
    runner.add_task(dummy_success, 5, label="slow")
    runner.add_task(dummy_success, 0, label="dependent", depends_on=["slow"])
    results = runner.run(verify=False)

    assert results["slow"]["has_failed"] is True
    assert results["dependent"]["status"] == "Terminated"
    assert results["dependent"]["has_failed"] is True
