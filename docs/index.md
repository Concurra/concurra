<div align="center">
  <a href="https://pypi.org/project/concurra/">
    <img src="https://github.com/Concurra/concurra/blob/main/docs/concurra_logo.png?raw=true" alt="Concurra" width="300">
  </a>
  <div>
    <em>Concurra — Structured concurrency, effortless parallelism, built-in dependency management</em>
    <br>
    <br>
  </div>

  <!-- Badges -->
  <a href="https://github.com/Concurra/concurra/actions/workflows/python-tests.yml" target="_blank">
    <img src="https://github.com/Concurra/concurra/actions/workflows/python-tests.yml/badge.svg?event=push&branch=main" alt="Test">
  </a>
  <a href="https://github.com/Concurra/concurra/blob/main/LICENSE" target="_blank">
    <img src="https://img.shields.io/github/license/Concurra/concurra.svg" alt="License">
  </a>
  <a href="https://concurra.readthedocs.io/en/latest/" target="_blank">
    <img src="https://readthedocs.org/projects/concurra/badge/?version=latest" alt="Documentation Status">
  </a>
  <a href="https://pepy.tech/projects/concurra" target="_blank">
    <img src="https://static.pepy.tech/badge/concurra" alt="PyPI Downloads">
  </a>
  <a href="https://pypi.org/project/concurra" target="_blank">
    <img src="https://img.shields.io/pypi/v/concurra?color=%2334D058&label=pypi%20package" alt="Package version">
  </a>
  <a href="https://pypi.org/project/concurra" target="_blank">
    <img src="https://img.shields.io/pypi/pyversions/concurra.svg?color=%2334D058" alt="Supported Python versions">
  </a>
</div>

---

**Concurra** is a lightweight Python library for **concurrent and parallel task execution**, built to simplify the orchestration of complex workflows.
It provides a high-level interface for running tasks using threads or processes, while automatically handling **dependencies, timeouts, errors,** and **fast-fail** behavior.

With built-in support for **dependency management**, you can define execution chains where tasks wait for others to finish—allowing for flexible and safe coordination across multiple workers.
Whether you're handling I/O-bound or CPU-bound operations, Concurra helps you manage concurrency with minimal boilerplate.

---

# 🚀 Features

- ✅ **Simple API**: Add tasks and execute them in parallel with minimal setup.
- 🔀 **Parallel Task Execution**: Run multiple tasks concurrently using threading or multiprocessing.
- 🔗 **Dependency Management**: Define task dependencies to ensure correct execution order across complex pipelines.
- 💥 **Fast Fail Support**: Stop all tasks as soon as one fails (optional).
- ⚠️ **Error Handling**: Automatically captures exceptions and supports custom logging.
- 📊 **Progress & Status Tracking**: Track execution status and view structured results.
- 🔀 **Background Execution**: Run tasks asynchronously and fetch results later.
- 🧠 **Multiprocessing Support**: Bypass GIL for CPU-bound tasks using true parallelism.
- 🛑 **Abort Support**: Gracefully abort background task execution.
- ⏱️ **Timeouts**: Set a timeout per task to prevent long-running executions.

---

## ❓ Why Not Use Native Threading or Multiprocessing?

Python offers several ways to run tasks concurrently — `threading`, `multiprocessing`, `asyncio`, and executors like `ThreadPoolExecutor`. These are powerful tools, but they come with steep learning curves, hidden complexities, and minimal guardrails — especially when managing multiple interdependent tasks.

**Concurra** builds on top of these foundations to provide a **clean, opinionated abstraction** that simplifies concurrent execution, **dependency management**, and runtime control — so you can focus on *what* to execute rather than *how*. Acting as a smart orchestration layer, Concurra emphasizes **safe**, **structured**, and **configurable concurrency**, enabling developers to build **reliable task pipelines** without reinventing the wheel.

Concurra models task dependencies using principles of a **Directed Acyclic Graph (DAG)**. Each task declares its dependencies, and Concurra ensures correct execution order by resolving these relationships dynamically at runtime.

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

## Why Developers Love Concurra
- ***Fewer bugs:*** No manual thread/process management.
- ***More control:*** Configure concurrency, fast-fail, timeout, and logging easily.
- ***Safer pipelines:*** Tasks execute only when dependencies are met.
- ***Better visibility:*** Structured results help with monitoring and debugging.
- ***Great for pipelines:*** Ideal for data processing, test automation, ETL jobs, and more.

Whether you're running 3 tasks or 300, Concurra gives you composability, clarity, and control—all while making concurrent execution feel intuitive and safe.

---

# 📦 Installation

```bash
pip install concurra
```

---

# 🚀 Quick Start
Run your first parallel tasks in under a minute with Concurra.

This quick guide will walk you through how to:

- Set up a `TaskRunner` for concurrent execution
- Add tasks using any Python function
- Run and collect results with minimal boilerplate


---

***🧱 Step 1: Create a `TaskRunner` object***
Configure parallelism and behavior like maximum concurrency or timeout.

```python
import concurra

runner = concurra.TaskRunner(max_concurrency=2)
```

---

***➕ Step 2: Add your tasks***
Use .add_task() to queue up any callable with a label.

```python

def say_hello():
    return "Hello World"

def say_universe():
    return "Hello Universe"

runner.add_task(say_hello, label="greet_world")
runner.add_task(say_universe, label="greet_universe")
```
---

***▶️ Step 3: Run tasks and collect results***
Use .run() to execute the tasks concurrently and retrieve structured results.

```python
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

***⚠️ Important Notes:***
- A TaskRunner object can be run only once.
- Once run() or execute_in_background() is called, you cannot add more tasks.
- For a new batch of parallel tasks, create a new TaskRunner object and add required tasks.

---

# API Reference
### ⚙️ `TaskRunner` Class

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

***🔧 Parameter Reference:***

- **`max_concurrency` (int)** – Maximum number of tasks allowed to run in parallel. Defaults to `os.cpu_count()` if not specified.
- **`name` (str)** – Optional name for the runner instance, used in logs and display outputs.
- **`timeout` (float)** – Maximum duration (in seconds) for any task to complete. Tasks exceeding this are terminated.
- **`progress_stats` (bool)** – Whether to show real-time task progress in the console. Defaults to `True`.
- **`fast_fail` (bool)** – If `True`, execution halts as soon as any task fails. Remaining tasks are aborted.
- **`use_multiprocessing` (bool)** – Use multiprocessing (separate processes) instead of multithreading. Recommended for CPU-bound tasks.
- **`logger` (Logger)** – Custom Python `Logger` instance. If not provided, a default logger is used.
- **`log_errors` (bool)** – Whether to log exceptions that occur during task execution to the logger.
---

### ➕ `add_task()` Method

Use `.add_task()` to queue up functions to run concurrently.

```python
runner.add_task(some_function, arg1, arg2, label="task1", kwarg1=value1)
```

You can also specify dependencies between tasks to ensure correct execution order.
```python
runner.add_task(some_function, arg1, arg2, label="task2", depends_on=["task1"], kwarg1=value1)
```

***🔧 Parameter Reference:***

- **`task` (callable)** – The function or callable you want to execute in parallel.
- **`*args`** – Positional arguments to pass to the task.
- **`label` (str)** – A unique identifier for the task. If not provided, the task's ID number is used.
- **`depends_on` (list of str, optional)** – A list of labels that this task depends on. The task will execute only after all its dependencies are complete.
- **`**kwargs`** – Additional keyword arguments passed to the task.

***📝 Notes***
- Task labels must be unique per TaskRunner instance. Re-using a label raises a ValueError. 
- A task cannot depend on itself. 
- Immediate circular dependencies are detected and rejected (e.g., A → B and B → A).

This allows you to control execution order when tasks have prerequisites.

---

### 🏃‍♂️ `run()` Method

When you call `.run()` on a `TaskRunner` object, you can customize its behavior using the following parameters:

```python
results = runner.run(
    verify=True,
    raise_exception=False,
    error_message="Custom failure message"
)
```

***🔧 Parameter Reference:***

- **`verify` (bool)** – Whether to automatically check if all tasks succeeded after execution. If any task failed, it logs a report or raises an exception depending on the next flag.
- **`raise_exception` (bool)** – If `True`, raises a Python `Exception` when any task fails. If `False`, failures are logged but not raised.
- **`error_message` (str)** – Optional custom message to include if `raise_exception=True` and an error occurs.

These options are useful when you're integrating Concurra into pipelines, tests, or automated workflows and need fine-grained error control.

---

### 🎯 `execute_in_background()` Method

Starts executing tasks in the background without blocking the main thread. Useful when you want to initiate task execution and continue doing other things before fetching results later.

```python
runner.execute_in_background()
# ... continue with other work ...
```
***📝 Notes***
- This method does not return task results immediately.
- Once background execution starts, no new tasks can be added to the runner.
- Use get_background_results() to collect results once execution is complete.

---

### 🟢 `is_running()` Method

Checks whether the `TaskRunner` is currently executing tasks in the background.

Use this method to **poll or monitor execution state**, especially after calling `execute_in_background()`.

```python
if runner.is_running():
    print("Tasks are still running...")
else:
    print("All tasks are done!")
```
***Returns: (bool)***
- Returns True if task execution is in progress.
- Returns False if all tasks have completed or if .run() / get_background_results() has already returned.

---

### 📥 `get_background_results()` Method

Fetches and returns results after background execution has started using `execute_in_background()`.  
This call **blocks until all tasks are complete**, so manual polling with `is_running()` is **not necessary**.

```python
results = runner.get_background_results(
    verify=True,
    raise_exception=False,
    error_message="Something went wrong"
)
```
***🔧 Parameter Reference:***

- **`verify` (bool, optional)** – Whether to automatically check if all tasks succeeded after execution.
- **`raise_exception` (bool, optional)** – If True, raises a Python Exception when any task fails. If False, failures are logged but not raised.
- **`error_message` (str, optional)** –  Custom message to include if raise_exception=True and an error occurs.

Example:
```python
runner = concurra.TaskRunner()
runner.add_task(func1, label="t1")
runner.add_task(func2, label="t2")

runner.execute_in_background()

# do other stuff here...

# No need to poll using is_running() method, just call get_background_results it will  
results = runner.get_background_results()
```
***📝 Notes***
- get_background_results() blocks until all tasks are finished. 
- This method waits internally, so there's no need to use is_running() to poll task completion manually. 
- Results returned are identical in structure to those from .run().
- Calling get_background_results() without first calling execute_in_background() will raise an error.

---

### ⛔ `abort()` Method

Gracefully terminates all currently running background tasks.
Use this method only when you've started execution with `execute_in_background()` and want to cancel the operation before it finishes.

```python
runner.abort()
```

---
# ✅ Example: All Tasks Pass

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
***Console Output:***

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

***Output Results dict:***

```python
print(json.dumps(results, indent=4))
```
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

# ❌ Example: Partial Failures

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

***Console Output:***

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

***Output Results dict:***

```python
print(json.dumps(results, indent=4))
```
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

# ⛔ Example: Fast-Fail Enabled
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
***Console Output:***
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

***Output Results dict:***

```python
print(json.dumps(results, indent=4))
```
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

# ⌛ Example: Task Timeout Behavior
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

***Console Output:***
```
ERROR:concurra.core:Execution Failed
+--------------+--------+------------+------------+
| label        | task   | status     | duration   |
|--------------+--------+------------+------------|
| timeout_task | slow   | Terminated | 4.0 sec    |
+--------------+--------+------------+------------+
Task 'timeout_task' failed with error: TimeoutError
```

***Output Results dict:***

```python
print(json.dumps(results, indent=4))
```
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

# 🔗 Example: Dependent Tasks
Concurra supports dependency management—allowing you to specify which tasks must complete before others begin.
This is useful for creating execution chains or parallel pipelines where task order matters.

Simply pass the depends_on=["task_label"] argument to .add_task() and Concurra will automatically handle the execution sequence.

Below is a real-world example showing two dependent chains running in parallel, and a final task that depends on both chains completing.

```python
import time
import concurra

def fetch_user_data():
    time.sleep(1)
    return "user_data.csv"

def clean_data(file_name):
    time.sleep(1)
    return f"cleaned_{file_name}"

def transform_data(cleaned_file):
    time.sleep(1)
    return f"transformed_{cleaned_file}"

def train_model(transformed_file):
    time.sleep(2)
    return f"model_trained_on_{transformed_file}"

def fetch_logs():
    time.sleep(1)
    return "raw_logs.txt"

def parse_logs(log_file):
    time.sleep(1)
    return f"parsed_{log_file}"

def analyze_logs(parsed_file):
    time.sleep(2)
    return f"analysis_result_{parsed_file}"

def task_A():
    time.sleep(0.5)
    return "Task A"

def task_B():
    time.sleep(0.5)
    return "Task B"

def generate_report(processed_file):
    return f"Report: {processed_file})"

runner = concurra.TaskRunner(max_concurrency=3)

# Independent tasks
runner.add_task(task_A, label="task_A")
runner.add_task(task_B, label="task_B")

# Chain 1: User data pipeline
runner.add_task(fetch_user_data, label="fetch_data")
runner.add_task(clean_data, "user_data.csv", label="clean", depends_on=["fetch_data"])
runner.add_task(transform_data, "cleaned_user_data.csv", label="transform", depends_on=["clean"])
runner.add_task(train_model, "transformed_cleaned_user_data.csv", label="train", depends_on=["transform"])

# Chain 2: Log analysis pipeline
runner.add_task(fetch_logs, label="fetch_logs")
runner.add_task(parse_logs, "raw_logs.txt", label="parse_logs", depends_on=["fetch_logs"])
runner.add_task(analyze_logs, "parsed_raw_logs.txt", label="analyze_logs", depends_on=["parse_logs"])

# Task with multiple dependencies
runner.add_task(generate_report, "report.txt", label="generate_report", depends_on=["analyze_logs", "train"])

results = runner.run()

print("✅ Results Summary:")
for label, info in results.items():
    print(f"{label}: {info['status']} → {info['result']}")

```

***⚙️ Parallel Execution Diagram***
```
⏱ Parallel Execution Begins 

Worker 1         Worker 2         Worker 3          Worker 4
--------         --------         --------          --------
[task_A]         [task_B]         [fetch_data]      [fetch_logs]
                                   ↓                  ↓
                                 [clean]          [parse_logs]
                                   ↓                  ↓
                              [transform]       [analyze_logs]
                                   ↓                  ↓
                                [train]               /
                                   \_________________/
                                        ↓
                               [generate_report]

```

***✅ How It Works***
- `task_A` and `task_B` are independent and start immediately.
- There are two dependent chains:
> - User Data Pipeline: `fetch_data` → `clean` → `transform` → `train`
> - Log Analysis Pipeline: `fetch_logs` → `parse_logs` → `analyze_logs`
- generate_report waits for both train and analyze_logs to complete before executing
- All root-level tasks (fetch_data, fetch_logs, task_A, task_B) can begin at the same time, governed by max_concurrency.
- Tasks within each chain start only after their dependencies have successfully finished.
- Independent tasks (task_A, task_B) finish early, freeing up workers for dependent tasks. 
- Concurra automatically manages execution order and resource usage, ensuring tasks run as early as possible while respecting dependencies.

---

# 🔐 License
MIT License.