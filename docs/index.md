# Concurra

**Concurra** is a Python library for parallel task execution made simple. It provides a high-level interface for managing and executing tasks concurrently using either threads or processes. With built-in features for error handling, timeouts, fast-fail behavior, and progress tracking, Concurra streamlines parallelism without the boilerplate.

---

## 🚀 Features

- ✅ **Simple API**: Add tasks and execute them in parallel with minimal setup.
- 🔀 **Parallel Task Execution**: Run multiple tasks concurrently using threading or multiprocessing.
- 💥 **Fast Fail Support**: Stop all tasks as soon as one fails (optional).
- ⚠️ **Error Handling**: Automatically captures exceptions and supports custom logging.
- 📊 **Progress & Status Tracking**: Track execution status and view structured results.
- 🔀 **Background Execution**: Run tasks asynchronously and fetch results later.
- 🧠 **Multiprocessing Support**: Bypass GIL for CPU-bound tasks using true parallelism.
- 🛑 **Abort Support**: Gracefully abort background task execution.
- ⏱️ **Timeouts**: Set a timeout per task to prevent long-running executions.

---

## Why Not Just Use Native `threading` or `multiprocessing`?

Python offers `threading`, `multiprocessing`, and executors like `ThreadPoolExecutor`. These are great—but Concurra adds structure, safety, and simplicity:

| Challenge Using Native APIs                       | How Concurra Solves It                                     |
| ------------------------------------------------- | ---------------------------------------------------------- |
| Setting up thread/process pools                   | ✅ Built-in with `max_concurrency`, no boilerplate          |
| Handling exceptions from worker threads/processes | ✅ Automatically captured, logged, and available in results |
| Task identification                               | ✅ Assign unique labels for tracking and debugging          |
| Terminating long-running or stuck tasks           | ✅ Built-in timeout and `abort()` support                   |
| Ensuring a task runner is only used once          | ✅ Enforced internally—no accidental re-use                 |
| Progress logging                                  | ✅ Automatic progress display and task status updates       |
| Fast fail if a task breaks                        | ✅ Opt-in `fast_fail` support for early termination         |
| Safe background execution                         | ✅ `execute_in_background()` and `get_background_results()` |
| Verifying task success                            | ✅ One-call `verify()` to ensure everything worked          |
| Preventing duplicate task labels                  | ✅ Built-in validation                                      |

---

🧠 How Concurra Works

To use Concurra effectively, follow these steps:

- Create a TaskRunner object – Configure parallelism and behavior (e.g. max workers, timeout).

- Add tasks using .add_task() – You can add any callable with args and a label.

- Run tasks using .run() or .execute_in_background() – Starts concurrent execution.

⚠️ Important Notes:

- A TaskRunner object can be run only once.

- Once run() or execute_in_background() is called, you cannot add more tasks.

- For a new batch of parallel tasks, create a new TaskRunner object and add required tasks.

---

## 📦 Installation

```bash
pip install concurra
```

## ⚙️ TaskRunner Options and Configuration

When initializing `TaskRunner`, you can customize behavior using the following parameters:

```python
runner = concurra.TaskRunner(
    max_concurrency=4,
    name="MyRunner",
    timeout=10,
    progress_stats=True,
    fast_fail=True,
    use_multiprocessing=False,
    logger=my_logger,
    log_errors=True
)
```

### Option Descriptions:

- **`max_concurrency` (int)** – Maximum number of tasks allowed to run in parallel. Defaults to `os.cpu_count()` if not specified.
- **`name` (str)** – Optional name for the runner instance, used in logs and display outputs.
- **`timeout` (float)** – Maximum duration (in seconds) for any task to complete. Tasks exceeding this are terminated.
- **`progress_stats` (bool)** – Whether to show real-time task progress in the console. Defaults to `True`.
- **`fast_fail` (bool)** – If `True`, execution halts as soon as any task fails. Remaining tasks are aborted.
- **`use_multiprocessing` (bool)** – Use multiprocessing (separate processes) instead of multithreading. Recommended for CPU-bound tasks.
- **`logger` (Logger)** – Custom Python `Logger` instance. If not provided, a default logger is used.
- **`log_errors` (bool)** – Whether to log exceptions that occur during task execution to the logger.
---

## ➕ `add_task()` Method Options

Use `.add_task()` to queue up functions to run concurrently.

```python
runner.add_task(some_function, arg1, arg2, label="task_name", kwarg1=value1)
```

### Option Descriptions:

- **`task` (callable)** – The function or callable you want to execute in parallel.
- **`*args`** – Positional arguments to pass to the task.
- **`label` (str)** – A unique identifier for the task. If not provided, the task's ID number is used.
- **`**kwargs`** – Additional keyword arguments passed to the task.

> 🔐 Note: Task labels must be unique per runner instance. Re-using a label raises a `ValueError`.

---

## 🏃‍♂️ `run()` Method Options

When you call `.run()` on a `TaskRunner` object, you can customize its behavior using the following parameters:

```python
results = runner.run(
    verify=True,
    raise_exception=False,
    error_message="Custom failure message"
)
```

### Option Descriptions:

- **`verify` (bool)** – Whether to automatically check if all tasks succeeded after execution. If any task failed, it logs a report or raises an exception depending on the next flag.
- **`raise_exception` (bool)** – If `True`, raises a Python `Exception` when any task fails. If `False`, failures are logged but not raised.
- **`error_message` (str)** – Optional custom message to include if `raise_exception=True` and an error occurs.

These options are useful when you're integrating Concurra into pipelines, tests, or automated workflows and need fine-grained error control.

---

## 👋 Hello World (Quick Start)

Run your first parallel tasks in under a minute:

```python
import concurra

def say_hello():
    return "Hello World"

def say_universe():
    return "Hello Universe"

runner = concurra.TaskRunner(max_concurrency=2)
runner.add_task(say_hello, label="greet_world")
runner.add_task(say_universe, label="greet_universe")

results = runner.run()
print(results)
```

🧪 Output:
```json
{
    "greet_world": {
        "task_name": "say_hello",
        "status": "Successful",
        "result": "Hello World",
        "has_failed": false
    },
    "greet_universe": {
        "task_name": "say_universe",
        "status": "Successful",
        "result": "Hello Universe",
        "has_failed": false
    }
}
```
---

## ✅ Basic Usage (All Tasks Pass)

```python
import concurra
import time
import json

def square(x):
    time.sleep(1)
    return x * x

def divide(x, y):
    return x / y

runner = concurra.TaskRunner(max_concurrency=4)  # Uses 4 workers

runner.add_task(square, 4, label="square_4")
runner.add_task(square, 5, label="square_5")
runner.add_task(divide, 10, 2, label="divide_10_2")

results = runner.run()

print(json.dumps(results, indent=4))
```

### Example Output (All Successful):

#### Console Output:

```
INFO:concurra.core:Concurra progress: [########.................] 1/3 [33.33%] in 0 min 0.0 sec
INFO:concurra.core:Concurra progress: [#################........] 2/3 [66.67%] in 0 min 1.04 sec
INFO:concurra.core:Concurra progress: [#########################] 3/3 [100.0%] in 0 min 1.04 sec
INFO:concurra.core:
+-------------+--------+------------+------------+
| label       | task   | status     | duration   |
|-------------+--------+------------+------------|
| square_4    | square | Successful | 1.01 sec   |
| square_5    | square | Successful | 1.01 sec   |
| divide_10_2 | divide | Successful | 0.0 sec    |
+-------------+--------+------------+------------+
```

#### Output Results dict:
`print(json.dumps(results, indent=4))`
```json
{
    "square_4": {
        "task_name": "square",
        "start_time": "2025-04-12 00:46:54",
        "end_time": "2025-04-12 00:46:55",
        "duration": "1.01 sec",
        "duration_seconds": 1.01,
        "result": 16,
        "error": null,
        "trace": null,
        "status": "Successful",
        "has_failed": false
    },
    "square_5": {
        "task_name": "square",
        "start_time": "2025-04-12 00:46:54",
        "end_time": "2025-04-12 00:46:55",
        "duration": "1.01 sec",
        "duration_seconds": 1.01,
        "result": 25,
        "error": null,
        "trace": null,
        "status": "Successful",
        "has_failed": false
    },
    "divide_10_2": {
        "task_name": "divide",
        "start_time": "2025-04-12 00:46:54",
        "end_time": "2025-04-12 00:46:54",
        "duration": "0.0 sec",
        "duration_seconds": 0.0,
        "result": 5.0,
        "error": null,
        "trace": null,
        "status": "Successful",
        "has_failed": false
    }
}
```

---

## ⚙️ Advanced Examples (Mixed, Failed, Timed Out, Fail Fast etc.)

### ❌ Example with Partial Failures

```python
import concurra
import time
import json

def square(x):
    time.sleep(1)
    return x * x

def divide(x, y):
    return x / y

runner = concurra.TaskRunner(max_concurrency=4)

runner.add_task(square, 4, label="square_4")
runner.add_task(square, 5, label="square_5")
runner.add_task(divide, 10, 2, label="divide_10_2")
runner.add_task(divide, 10, 0, label="divide_by_zero")  # This will fail

results = runner.run()

print(json.dumps(results, indent=4))
```

### Output with Errors (Console)

```
INFO:concurra.core:Concurra progress: [######...................] 1/4 [25.0%] in 0 min 0.0 sec
INFO:concurra.core:Concurra progress: [############.............] 2/4 [50.0%] in 0 min 0.1 sec
INFO:concurra.core:Concurra progress: [###################......] 3/4 [75.0%] in 0 min 1.04 sec
INFO:concurra.core:Concurra progress: [#########################] 4/4 [100.0%] in 0 min 1.04 sec
ERROR:concurra.core:Execution Failed
+----------------+--------+------------+------------+
| label          | task   | status     | duration   |
|----------------+--------+------------+------------|
| square_4       | square | Successful | 1.0 sec    |
| square_5       | square | Successful | 1.01 sec   |
| divide_10_2    | divide | Successful | 0.0 sec    |
| divide_by_zero | divide | Failed     | 0.0 sec    |
+----------------+--------+------------+------------+
Task 'divide_by_zero' failed with error: ZeroDivisionError: division by zero 
 Traceback (most recent call last):
  File "../concurra/concurra/core.py", line 52, in run
    result = self.task_handler.run()
             ^^^^^^^^^^^^^^^^^^^^^^^
  File "../concurra/concurra/core.py", line 207, in run
    return self.task(*self.args, **self.kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<stdin>", line 2, in divide
ZeroDivisionError: division by zero
```

#### Output Results dict:
`print(json.dumps(results, indent=4))`
```json
{
    "square_4": {
        "task_name": "square",
        "start_time": "2025-04-12 00:49:23",
        "end_time": "2025-04-12 00:49:24",
        "duration": "1.0 sec",
        "duration_seconds": 1.0,
        "result": 16,
        "error": null,
        "trace": null,
        "status": "Successful",
        "has_failed": false
    },
    "square_5": {
        "task_name": "square",
        "start_time": "2025-04-12 00:49:23",
        "end_time": "2025-04-12 00:49:24",
        "duration": "1.01 sec",
        "duration_seconds": 1.01,
        "result": 25,
        "error": null,
        "trace": null,
        "status": "Successful",
        "has_failed": false
    },
    "divide_10_2": {
        "task_name": "divide",
        "start_time": "2025-04-12 00:49:23",
        "end_time": "2025-04-12 00:49:23",
        "duration": "0.0 sec",
        "duration_seconds": 0.0,
        "result": 5.0,
        "error": null,
        "trace": null,
        "status": "Successful",
        "has_failed": false
    },
    "divide_by_zero": {
        "task_name": "divide",
        "start_time": "2025-04-12 00:49:23",
        "end_time": "2025-04-12 00:49:23",
        "duration": "0.0 sec",
        "duration_seconds": 0.0,
        "result": null,
        "error": "ZeroDivisionError: division by zero",
        "trace": "Traceback (most recent call last):\n  File \"//concurra/concurra/concurra/core.py\", line 52, in run\n    result = self.task_handler.run()\n             ^^^^^^^^^^^^^^^^^^^^^^^\n  File \"//concurra/concurra/concurra/core.py\", line 207, in run\n    return self.task(*self.args, **self.kwargs)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"<stdin>\", line 2, in divide\nZeroDivisionError: division by zero\n",
        "status": "Failed",
        "has_failed": true
    }
}
```

---

### ⛔ Fast Fail on First Error
**Fast Fail (fast_fail=True):** When enabled, TaskRunner will immediately terminate all other tasks as soon as any task fails. This is useful when one failure invalidates the rest of the work or when you want to save resources
```python
import concurra
import time

def will_fail():
    raise RuntimeError("Oops!")

def will_succeed():
    time.sleep(2)
    return "Success"

runner = concurra.TaskRunner(fast_fail=True, max_concurrency=2)
runner.add_task(will_succeed, label="ok")
runner.add_task(will_fail, label="fail")
runner.run()
```
#### Console Output:
```
ERROR:concurra.core:terminating execution !
INFO:concurra.core:Deleting terminated task: ok, will_succeed
ERROR:concurra.core:Execution Failed
+---------+--------------+------------+------------+
| label   | task         | status     | duration   |
|---------+--------------+------------+------------|
| ok      | will_succeed | Terminated | 0.11 sec   |
| fail    | will_fail    | Failed     | 0.0 sec    |
+---------+--------------+------------+------------+
Task 'ok' failed with error: TimeoutError:  
 None
Task 'fail' failed with error: RuntimeError: Oops! 
 Traceback (most recent call last):
  File "/concurra/concurra/core.py", line 52, in run
    result = self.task_handler.run()
             ^^^^^^^^^^^^^^^^^^^^^^^
  File "/concurra/concurra/core.py", line 207, in run
    return self.task(*self.args, **self.kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<stdin>", line 2, in will_fail
RuntimeError: Oops!
```

#### Output Results dict:
`print(json.dumps(results, indent=4))`
```json
{
    "ok": {
        "task_name": "will_succeed",
        "start_time": "2025-04-12 00:56:15",
        "end_time": "2025-04-12 00:56:16",
        "duration": "0.11 sec",
        "duration_seconds": 0.11,
        "result": null,
        "error": "TimeoutError: ",
        "trace": null,
        "status": "Terminated",
        "has_failed": true
    },
    "fail": {
        "task_name": "will_fail",
        "start_time": "2025-04-12 00:56:15",
        "end_time": "2025-04-12 00:56:15",
        "duration": "0.0 sec",
        "duration_seconds": 0.0,
        "result": null,
        "error": "RuntimeError: Oops!",
        "trace": "Traceback (most recent call last):\n  File \"/concurra/concurra/core.py\", line 52, in run\n    result = self.task_handler.run()\n             ^^^^^^^^^^^^^^^^^^^^^^^\n  File \"//concurra/concurra/concurra/core.py\", line 207, in run\n    return self.task(*self.args, **self.kwargs)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"<stdin>\", line 2, in will_fail\nRuntimeError: Oops!\n",
        "status": "Failed",
        "has_failed": true
    }
}
```

### ⌛ Task Timeout
**Timeout (timeout=SECONDS):** Each task is assigned a maximum allowed time to run. If a task takes longer than this, it will be forcefully stopped and reported as Terminated. This is critical to prevent long-running or hanging operations from blocking your system.
```python
import concurra
import time

def slow():
    time.sleep(15)
    return "Done"

runner = concurra.TaskRunner(timeout=4)
runner.add_task(slow, label="timeout_task")
results = runner.run()
print(results["timeout_task"]["status"])  # Terminated
```

#### Console Output:
```
ERROR:concurra.core:Execution Failed
+--------------+--------+------------+------------+
| label        | task   | status     | duration   |
|--------------+--------+------------+------------|
| timeout_task | slow   | Terminated | 4.0 sec    |
+--------------+--------+------------+------------+
Task 'timeout_task' failed with error: TimeoutError
```

#### Output Results dict:
`print(json.dumps(results, indent=4))`
```json
{
    "timeout_task": {
        "task_name": "slow",
        "start_time": "2025-04-12 00:57:51",
        "end_time": "2025-04-12 00:57:55",
        "duration": "4.0 sec",
        "duration_seconds": 4.0,
        "result": null,
        "error": "TimeoutError: ",
        "trace": null,
        "status": "Terminated",
        "has_failed": true
    }
}
```

---

## 🧪 Testing

```bash
pytest -sv
```

---

## 🔐 License

MIT License.

