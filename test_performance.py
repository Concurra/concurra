import time
import pytest


from concurra import TaskRunner

def dummy_success(x):
    pass

def test_add_1m_tasks():

    start = time.time()
    runner = TaskRunner(max_concurrency=2)

    for _ in range(1_000_000):
        runner.add_task(dummy_success)

    end = time.time()
    assert end - start < 10
