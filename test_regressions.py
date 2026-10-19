"""Regression coverage for scheduling, worker failure, and cancellation."""

import os
import shlex
import subprocess
import sys
import threading
import time

import pytest

from concurra import TaskRunner
from concurra.core import CommandTaskHandler


def exit_worker():
    raise SystemExit(7)


def return_unpicklable_result():
    return threading.Lock()


def fail_task():
    raise ValueError("failed root")


def wait_for_file(path):
    deadline = time.monotonic() + 5
    while not path.exists() and time.monotonic() < deadline:
        time.sleep(.01)
    assert path.exists(), "Worker did not become ready"


@pytest.mark.parametrize("use_processes", [False, True])
def test_system_exit_is_failed_without_retry_and_blocks_dependents(use_processes):
    runner = TaskRunner(max_concurrency=1, use_multiprocessing=use_processes,
                        task_retries=2, fast_fail=True, progress_stats=False)
    runner.add_task(exit_worker, label="exit")
    runner.add_task(abs, -3, label="dependent", depends_on=["exit"])
    results = runner.run()
    assert results["exit"]["status"] == "Failed"
    assert results["exit"]["error"] == "SystemExit: 7"
    assert results["exit"]["attempts"] == 1
    assert results["dependent"]["status"] == "Terminated"


@pytest.mark.parametrize("exit_code", [0, 7])
@pytest.mark.parametrize("fast_fail", [False, True])
def test_process_exit_without_result_is_failure(exit_code, fast_fail):
    runner = TaskRunner(max_concurrency=1, use_multiprocessing=True,
                        fast_fail=fast_fail, progress_stats=False)
    runner.add_task(os._exit, exit_code, label="exit")
    runner.add_task(abs, -3, label="dependent", depends_on=["exit"])
    results = runner.run()
    assert results["exit"]["status"] == "Failed"
    assert "code {}".format(exit_code) in results["exit"]["error"]
    assert results["dependent"]["status"] == "Terminated"


def test_unpicklable_result_has_structured_failure():
    runner = TaskRunner(use_multiprocessing=True, progress_stats=False)
    runner.add_task(return_unpicklable_result, label="lock")
    results = runner.run()
    assert results["lock"]["status"] == "Failed"
    assert "Could not record task result:" in results["lock"]["error"]
    assert results["lock"]["result"] is None
    assert results["lock"]["attempts"] == 1
    assert results["lock"]["trace"]


@pytest.mark.parametrize("fast_fail", [False, True])
def test_initial_pickle_failures_do_not_strand_pending_tasks(fast_fail):
    runner = TaskRunner(max_concurrency=1, use_multiprocessing=True,
                        fast_fail=fast_fail, progress_stats=False)
    runner.add_task(lambda: None, label="bad1")
    runner.add_task(lambda: None, label="bad2")
    runner.add_task(abs, -3, label="good")
    results = runner.run()
    assert results["bad1"]["status"] == "Failed"
    assert results["bad2"]["status"] == ("Terminated" if fast_fail else "Failed")
    assert results["good"]["status"] == ("Terminated" if fast_fail else "Successful")


def test_start_failure_does_not_strand_pending_tasks(monkeypatch):
    runner = TaskRunner(max_concurrency=1, progress_stats=False)
    runner.add_task(abs, -1, label="bad")
    runner.add_task(abs, -2, label="good")

    def start_failure():
        raise RuntimeError("cannot start worker")

    monkeypatch.setattr(runner.tasks[0], "start", start_failure)
    results = runner.run()
    assert results["bad"]["status"] == "Failed"
    assert results["good"]["result"] == 2


@pytest.mark.parametrize("background", [False, True])
def test_reverse_dependency_failure_chain_is_fully_resolved(background):
    runner = TaskRunner(max_concurrency=1, progress_stats=False)
    runner.add_task(abs, -1, label="C", depends_on=["B"])
    runner.add_task(abs, -2, label="B", depends_on=["A"])
    runner.add_task(fail_task, label="A")
    if background:
        runner.execute_in_background()
        results = runner.get_background_results()
    else:
        results = runner.run()
    assert results["A"]["status"] == "Failed"
    assert results["B"]["status"] == results["C"]["status"] == "Terminated"
    assert not runner.tasks
    assert runner._executed_tasks == len(runner)


@pytest.mark.parametrize("cancellation", ["abort", "timeout", "fast_fail"])
def test_cancelled_thread_never_retries(cancellation):
    entered = threading.Event()
    release = threading.Event()
    calls = []

    def task():
        calls.append(1)
        entered.set()
        release.wait(5)
        raise ValueError("transient failure")

    def failure_after_task_starts():
        assert entered.wait(5)
        raise ValueError("stop execution")

    runner = TaskRunner(max_concurrency=2, task_retries=2, progress_stats=False,
                        fast_fail=cancellation == "fast_fail",
                        timeout=.1 if cancellation == "timeout" else None)
    runner.add_task(task, label="retry")
    worker = runner.tasks[0]
    if cancellation == "fast_fail":
        runner.add_task(failure_after_task_starts, label="failure", task_retries=0)
    try:
        runner.execute_in_background()
        assert entered.wait(5)
        results = runner.abort() if cancellation == "abort" else runner.get_background_results()
        assert results["retry"]["status"] == "Terminated"
    finally:
        release.set()
        worker.executor.join(timeout=5)
    assert calls == [1]
    assert runner.results_registry["retry"]["status"] == "Terminated"


@pytest.mark.parametrize("cancellation", ["abort", "timeout"])
def test_cancelled_command_never_retries(tmp_path, cancellation):
    attempts = tmp_path / "attempts"
    code = (
        "import time; from pathlib import Path; "
        "p=Path({!r}); p.open('a').write('attempt\\n'); time.sleep(5)"
    ).format(str(attempts))
    runner = TaskRunner(task_retries=2, progress_stats=False)
    runner.add_command([sys.executable, "-c", code], label="command")
    worker = runner.tasks[0]
    runner.execute_in_background()
    try:
        wait_for_file(attempts)
        if cancellation == "timeout":
            runner.timeout = .01
            results = runner.get_background_results()
        else:
            results = runner.abort()
        worker.executor.join(timeout=2)
        assert not worker.executor.is_alive()
        assert results["command"]["status"] == "Terminated"
        assert attempts.read_text().splitlines() == ["attempt"]
    finally:
        worker.terminate()


@pytest.mark.parametrize("shell", [False, True])
@pytest.mark.parametrize("cancellation", ["abort", "timeout"])
def test_cancelled_command_stops_descendants(tmp_path, shell, cancellation):
    ready = tmp_path / "ready"
    release = tmp_path / "release"
    completed = tmp_path / "completed"
    child_code = """
import time
from pathlib import Path
ready, release, completed = map(Path, {paths!r})
ready.touch()
deadline = time.monotonic() + 5
while not release.exists() and time.monotonic() < deadline:
    time.sleep(.01)
if release.exists():
    completed.touch()
""".format(paths=[str(ready), str(release), str(completed)])
    # Use script paths so cmd.exe does not reinterpret quotes embedded in
    # nested Python -c strings before the cancellation test can even start.
    child_script = tmp_path / "child.py"
    child_script.write_text(child_code)
    parent_script = tmp_path / "parent.py"
    parent_script.write_text(
        "import subprocess, sys; subprocess.Popen([sys.executable, {!r}]).wait()".format(str(child_script)))
    command = [sys.executable, str(parent_script)]
    runner = TaskRunner(progress_stats=False)
    if shell:
        command_string = (subprocess.list2cmdline(command) if os.name == "nt"
                          else " ".join(shlex.quote(arg) for arg in command))
        runner.add_shell_command(command_string, label="command")
    else:
        runner.add_command(command, label="command")
    worker = runner.tasks[0]
    runner.execute_in_background()
    try:
        wait_for_file(ready)
        if cancellation == "timeout":
            runner.timeout = .01
            results = runner.get_background_results()
        else:
            results = runner.abort()
        release.touch()
        worker.executor.join(timeout=2)
        assert not worker.executor.is_alive()
        time.sleep(.1)
        assert results["command"]["status"] == "Terminated"
        assert not completed.exists(), "Descendant continued after cancellation"
    finally:
        worker.terminate()


def test_terminated_command_handler_cannot_start_later(tmp_path):
    marker = tmp_path / "unexpected"
    handler = CommandTaskHandler([
        sys.executable, "-c", "from pathlib import Path; Path({!r}).touch()".format(str(marker))])
    handler.terminate()
    with pytest.raises(RuntimeError, match="terminated"):
        handler.run()
    assert not marker.exists()


@pytest.mark.parametrize("members", ["", "123 Z\n", "456 S\n123 Z+\n"])
def test_macos_exited_group_permission_error_is_harmless(monkeypatch, members):
    from types import SimpleNamespace

    def denied(*args):
        raise PermissionError("group already exited")

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(os, "killpg", denied, raising=False)
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout=members))
    process = SimpleNamespace(pid=123, poll=lambda: 0)
    CommandTaskHandler._signal_process_group(process, 15)


@pytest.mark.parametrize("returncode,members", [(None, ""), (0, "123 S\n")])
def test_macos_live_group_permission_error_is_not_hidden(monkeypatch, returncode, members):
    from types import SimpleNamespace

    def denied(*args):
        raise PermissionError("live group denied")

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(os, "killpg", denied, raising=False)
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout=members))
    process = SimpleNamespace(pid=123, poll=lambda: returncode)
    with pytest.raises(PermissionError, match="live group denied"):
        CommandTaskHandler._signal_process_group(process, 15)


@pytest.mark.skipif(os.name != "posix", reason="POSIX process group semantics")
def test_timeout_kills_child_after_parent_exits_even_if_child_ignores_sigterm(tmp_path):
    ready = tmp_path / "ready"
    release = tmp_path / "release"
    completed = tmp_path / "completed"
    code = """
import signal, time
from pathlib import Path
signal.signal(signal.SIGTERM, signal.SIG_IGN)
Path({ready!r}).touch()
deadline = time.monotonic() + 5
while not Path({release!r}).exists() and time.monotonic() < deadline:
    time.sleep(.01)
if Path({release!r}).exists():
    Path({completed!r}).touch()
""".format(ready=str(ready), release=str(release), completed=str(completed))
    runner = TaskRunner(progress_stats=False)
    runner.add_shell_command(
        "{} -c {} &".format(shlex.quote(sys.executable), shlex.quote(code)), label="shell")
    worker = runner.tasks[0]
    runner.execute_in_background()
    try:
        wait_for_file(ready)
        worker.task_handler._process.wait(timeout=5)
        runner.timeout = .01
        results = runner.get_background_results()
        release.touch()
        worker.executor.join(timeout=2)
        assert not worker.executor.is_alive()
        assert results["shell"]["status"] == "Terminated"
        time.sleep(.1)
        assert not completed.exists()
    finally:
        worker.terminate()


def test_command_retry_success_preserves_binary_output_cwd_and_env(tmp_path):
    code = (
        "import os, sys; from pathlib import Path; "
        "p=Path('attempt'); previous=p.exists(); p.touch(); "
        "sys.stdout.buffer.write(os.environ['CONCURRA_TEST_VALUE'].encode()); "
        "sys.exit(0 if previous else 1)"
    )
    runner = TaskRunner(task_retries=1, progress_stats=False)
    runner.add_command([sys.executable, "-c", code], label="command", cwd=tmp_path,
                       env={"CONCURRA_TEST_VALUE": "payload"}, text=False)
    result = runner.run(raise_exception=True)["command"]
    assert result["status"] == "Successful"
    assert result["attempts"] == 2
    assert result["retried"] is True
    assert len(result["retry_errors"]) == 1
    assert result["result"] == result["output"]
    assert result["result"]["stdout"] == b"payload"
    assert result["result"]["cwd"] == str(tmp_path)
    assert (tmp_path / "attempt").exists()


@pytest.mark.parametrize("limit", [0, -1])
def test_nonpositive_concurrency_is_one(limit):
    runner = TaskRunner(max_concurrency=limit, progress_stats=False)
    runner.add_task(abs, -2)
    assert runner.max_concurrency == 1
    assert runner.run()[0]["result"] == 2


def test_unknown_cpu_count_defaults_to_one(monkeypatch):
    monkeypatch.setattr(os, "cpu_count", lambda: None)
    assert TaskRunner().max_concurrency == 1


@pytest.mark.parametrize("limit", [1.5, "2"])
def test_invalid_concurrency_rejected_at_construction(limit):
    with pytest.raises(TypeError):
        TaskRunner(max_concurrency=limit)


def test_dependency_chain_beyond_recursion_limit():
    runner = TaskRunner(progress_stats=False)
    length = sys.getrecursionlimit() + 50
    for label in range(length):
        runner.add_task(abs, -label, label=label,
                        depends_on=[label - 1] if label else [])
    assert len(runner) == length


def test_long_cycle_is_rejected_without_recursion_error():
    runner = TaskRunner(progress_stats=False)
    length = sys.getrecursionlimit() + 50
    for label in range(length):
        runner.add_task(abs, -label, label=label, depends_on=[label + 1])
    with pytest.raises(ValueError, match="Circular dependency"):
        runner.add_task(abs, 0, label=length, depends_on=[0])


def test_failed_retry_does_not_retain_previous_attempt_output():
    class ResultError(ValueError):
        result = "old output"

    calls = []

    def task():
        calls.append(1)
        if len(calls) == 1:
            raise ResultError("first attempt")
        raise ValueError("second attempt")

    runner = TaskRunner(task_retries=1, progress_stats=False)
    runner.add_task(task, label="retry")
    result = runner.run()["retry"]
    assert result["status"] == "Failed"
    assert result["result"] is None
    assert result["attempts"] == 2
