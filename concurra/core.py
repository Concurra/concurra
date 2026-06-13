import os
import time
import traceback
import threading
import multiprocessing
import logging
from collections.abc import Iterable, Mapping
from datetime import datetime
from multiprocessing.reduction import ForkingPickler
from tabulate import tabulate

LOGGER = logging.getLogger(__name__)


class TaskExecutor:
    """
    class for executing tasks while recording runtime results and statistics.
    """

    def __init__(self, task_handler, task_id, label, results_registry, use_multiprocessing=False,
                 depends_on=None):
        """
        Initialize the executor.

        Args:
            task_handler: The object that defines a `.run()` method for the task.
            task_id: Unique identifier for the task execution.
            label: Key used to store results in the results_registry.
            results_registry: Dictionary to store execution metadata and results.
            depends_on: list of dependencies task labels
        """

        self.task_handler = task_handler
        self.task_name = task_handler.name
        self.task_id = task_id
        self.label = label
        self.results_registry = results_registry
        self.use_multiprocessing = use_multiprocessing
        self._results_lock = None if use_multiprocessing else threading.Lock()
        self._externally_terminated = False
        self.execution_mode = None
        self.warning = None
        self.executor = None
        self.time_started = None
        self.time_finished = None
        self._has_started = False
        self._init_results_registry()
        self.depends_on = set(depends_on or [])

    def __str__(self):
        return f"<TaskExecutor {self.label}[#{self.task_id}] {self.task_handler}>"

    def run(self):
        """
        Execute the task and record results and errors, if any.
        """
        result, err_message, has_failed, trace_log = None, None, False, None
        self.time_started = datetime.now()

        try:
            result = self.task_handler.run()
        except Exception as e:
            has_failed = True
            trace_log = traceback.format_exc()
            err_message = f"{type(e).__name__}: {str(e)}"
        finally:
            self._record_results(result, has_failed, err_message, trace_log)

    def join(self):
        """
        Block until the executor (e.g., thread or process) completes.
        """
        if self.executor:
            self.executor.join()

    def update_results_on_termination(self, error=None):
        """
        Force-update the results registry in case the task is externally terminated.

        Args:
            error: The exception instance that caused termination.
        """
        if error is None:
            error = TimeoutError()

        error_details = f"{type(error).__name__}: {str(error)}"
        self._record_results(None, True, error_details, None, status="Terminated")

    def update_results_on_failure(self, error, warning=None, execution_mode=None):
        """
        Force-update the results registry for a task that failed before it could run.
        """
        if warning:
            self.warning = warning
        if execution_mode is not None:
            self.execution_mode = execution_mode

        error_details = f"{type(error).__name__}: {str(error)}"
        trace_log = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        self._record_results(None, True, error_details, trace_log, status="Failed")

    def use_thread_fallback(self, warning):
        """
        Run this task in a thread even though the runner normally uses processes.
        """
        self.use_multiprocessing = False
        self._results_lock = threading.Lock()
        self.execution_mode = "thread_fallback"
        self.warning = warning

    def is_results_updated(self):
        """
        Check if the results registry has been updated for this task.

        Returns:
            bool: True if results are stored, else False.
        """
        return bool(self.results_registry.get(self.label))

    def start(self):
        if self.is_running():
            raise RuntimeError("Already running")
        
        if self.use_multiprocessing:
            self.executor = multiprocessing.Process(target=self.run)
            if self.execution_mode is None:
                self.execution_mode = "process"
        else:
            self.executor = threading.Thread(target=self.run)
            if self.execution_mode is None:
                self.execution_mode = "thread"
        
        self.executor.daemon = True
        self.time_started = datetime.now()
        self._has_started = True
        self.executor.start()

    def terminate(self):
        if self.executor is not None:
            if self.use_multiprocessing:
                self.executor.terminate()  # For processes

    def is_running(self):
        return self.executor is not None and self.executor.is_alive()

    @property
    def exitcode(self):
        """
        Return an exit code if task has finished; else None.

        Returns:
            int or None
        """
        return 0 if self._has_started and not self.is_running() else None

    @property
    def has_failed(self):
        """
        Indicates whether the task execution failed due to an exception.

        Returns:
            bool
        """
        return self.results_registry[self.label].get("has_failed", False)

    def _init_results_registry(self):
        """
        Initialize the results entry in the results registry for this task.
        """
        self.results_registry[self.label] = {}

    def _record_results(self, result, has_failed, err_message, trace_log, status=None):
        if self._results_lock:
            with self._results_lock:
                return self._record_results_unlocked(result, has_failed, err_message, trace_log, status)
        return self._record_results_unlocked(result, has_failed, err_message, trace_log, status)

    def _is_already_terminated(self):
        """
        Whether this task has already been marked "Terminated".

        Uses the in-process flag (fast path, covers threads) and, for
        multiprocessing, falls back to the shared registry so a still-running
        worker process won't overwrite a termination recorded by the parent.
        """
        if self._externally_terminated:
            return True
        if self.use_multiprocessing:
            existing = self.results_registry.get(self.label)
            return bool(existing) and existing.get("status") == "Terminated"
        return False

    def _record_results_unlocked(self, result, has_failed, err_message, trace_log, status=None):
        """
        Store execution results, stats, and metadata in the results registry.

        Args:
            result: The output of the task handler's run method.
            has_failed: Boolean indicating if an error occurred.
            err_message: String representation of any error encountered.
            trace_log: Full traceback as string.
            status: Optional override for result status (e.g., "Terminated").
        """
        if not status:
            status = "Failed" if has_failed else "Successful"

        # Never let a normal result overwrite a "Terminated" one. For threads the
        # in-process flag is enough; for multiprocessing the worker is a separate
        # process (its own copy of the flag), so we also consult the shared
        # results registry, which the parent updates on termination.
        if status != "Terminated" and self._is_already_terminated():
            return
        if status == "Terminated":
            self._externally_terminated = True

        self.time_finished = datetime.now()
        if not self.time_started:
            self.time_started = self.time_finished

        duration_seconds = round((self.time_finished - self.time_started).total_seconds(), 2)
        duration_display = (
            f"{round(duration_seconds / 60, 2)} min" if duration_seconds > 60 else f"{duration_seconds} sec"
        )

        self.results_registry[self.label] = {
            "task_name": str(self.task_handler.name),
            "start_time": self.time_started.strftime("%Y-%m-%d %H:%M:%S") if self.time_started else None,
            "end_time": self.time_finished.strftime("%Y-%m-%d %H:%M:%S") if self.time_finished else None,
            "duration": duration_display,
            "duration_seconds": duration_seconds,
            "result": result,
            "error": err_message,
            "trace": trace_log,
            "status": status,
            "has_failed": has_failed,
            "output": result,
            "execution_mode": self.execution_mode,
            "warning": self.warning
        }


class TaskHandler:
    """
    A class to wrap a task (function or callable) along with its arguments and 
    provide an interface to execute it.

    Attributes:
        task (callable): The task (function or callable) to execute.
        args (tuple): Positional arguments to pass to the task.
        kwargs (dict): Keyword arguments to pass to the task.
        name (str): The name of the task (function name or string representation).
    """

    def __init__(self, task, *args, **kwargs):
        """
        Initialize the TaskHandler with the given task and arguments.

        Args:
            task (callable): The function or callable to execute.
            *args: Positional arguments to pass to the task.
            **kwargs: Keyword arguments to pass to the task.
        """
        self.task = task
        self.args = args
        self.kwargs = kwargs
        self.name = getattr(task, '__name__', str(task))

    def run(self):
        """
        Execute the task with the provided arguments.

        Returns:
            The result of executing the task.
        """
        return self.task(*self.args, **self.kwargs)
    
    def __str__(self):
        """
        Return a string representation of the TaskHandler instance.

        Returns:
            str: A string representing the TaskHandler, including the task name.
        """
        return f"<TaskHandler: {self.name}>"


class TaskRunner:

    STATE_RUNNING = 0
    STATE_CLOSING = 1
    STATE_TERMINATED = 2
    MAINTENANCE_INTERVAL = 0.1  # seconds
    PROGRESS_LOG_DIVISOR = 10   # log progress every (total_tasks / this)
    SHUTDOWN_GRACE = 0.1        # seconds to wait when reaping/terminating tasks

    def __init__(self, max_concurrency=None, name=None, timeout=None, progress_stats=True, fast_fail=False, 
                 use_multiprocessing=False, logger=None, log_errors=False,
                 fallback_to_thread_on_pickle_error=False):
        """
        Initialize the TaskRunner.

        Args:
            max_concurrency (int): Maximum number of tasks allowed to run concurrently, either as threads or processes depending on configuration.
            name (str): Name for the task runner instance.
            timeout (float): Time in seconds to wait before terminating tasks.
            progress_stats (bool): Whether to log progress statistics.
            fast_fail (bool): Whether to stop execution when a task fails.
            use_multiprocessing (bool): Whether to use multiprocessing instead of multithreading.
            logger (Logger, optional): Custom logger instance to use for logging messages. 
            log_errors (bool): Whether to log errors encountered during task execution.
            fallback_to_thread_on_pickle_error (bool): When multiprocessing is enabled, run unpicklable tasks in a thread instead of marking them failed.
        """

        self.log = logger or LOGGER
        self.max_concurrency = max_concurrency or os.cpu_count()
        if self.max_concurrency < 1:
            self.log.warning("max_concurrency must be >= 1; resetting to 1, tasks will not run in parallel")
            self.max_concurrency = 1
        self.timeout = timeout
        self.name = name or self.__class__.__name__
        self.progress_stats = progress_stats
        self.fast_fail = fast_fail
        self.use_multiprocessing = use_multiprocessing
        self.log_errors = log_errors
        self.fallback_to_thread_on_pickle_error = fallback_to_thread_on_pickle_error

        if use_multiprocessing:
            manager = multiprocessing.Manager()
            self.results_registry = manager.dict()
        else:
            self.results_registry = dict()

        self.tasks = list()
        self.parents_of_label = dict()
        self.started_tasks = list()
        self.time_started = None

        self._task_handler = None
        self._total_tasks = 0
        self._executed_tasks = 0
        self._has_started = False
        self._terminating = False

        # Guards runner-level bookkeeping (started_tasks, counters, task sets)
        # that is mutated by both the maintenance thread and the caller thread
        # (e.g. abort()). Reentrant because _cleanup_finished_tasks may call
        # _terminate_tasks while already holding the lock.
        self._state_lock = threading.RLock()

        self._failed_tasks = set()
        self._terminated_tasks = set()
        self._successful_tasks = set()

    def __len__(self):
        return self._total_tasks

    def add_task(self, task, *args, label=None, depends_on=None, **kwargs):
        """
        Add a task to the task queue to be executed.

        Args:
            task (callable): The function or task handler to execute.
            *args: Arguments to pass to the task.
            label (str): Unique key label for the task (default is the task ID).
            depends_on (list): list of labels on which it depends
            **kwargs: Additional keyword arguments for the task.
        """
        self._add_task(task, args, kwargs, label=label, depends_on=depends_on)

    def _add_task(self, task, args, kwargs, label=None, depends_on=None):
        """
        Internal task registration that takes the task's ``args``/``kwargs`` as
        explicit containers rather than via ``*args``/``**kwargs``. This keeps
        the framework's ``label``/``depends_on`` parameters from colliding with
        task arguments that happen to share those names.
        """
        if self._has_started:
            raise RuntimeError("Cannot add tasks after execution has started.")

        if not callable(task):
            raise TypeError(f"The provided task '{task}' is not callable.")

        task_id = len(self.tasks)
        if label is None:
            label = task_id
        depends_on = set(depends_on or [])

        if label in self.parents_of_label:
            raise ValueError(f"Duplicate task key label: '{label}' already exists.")

        if label in depends_on:
            raise ValueError(f"Task '{label}' cannot depend on itself.")

        if depends_on:
            cycle = self._find_cycle_from_new_task(label, depends_on)
            if cycle:
                raise ValueError(f"Circular dependency detected: {' -> '.join(str(node) for node in cycle)}.")

        task_handler = TaskHandler(task, *args, **kwargs)
        task_executor = TaskExecutor(task_handler, task_id, label, self.results_registry,
                                     use_multiprocessing=self.use_multiprocessing,
                                     depends_on=depends_on)
        self.tasks.append(task_executor)
        self.parents_of_label[label] = depends_on
        self._total_tasks += 1

    def add_func(self, func, *args, **kwargs):
        """
        Add a task, using the reserved ``key`` keyword as its unique label.

        Args:
            func (callable): The function to execute.
            *args: Positional arguments forwarded to ``func``.
            **kwargs: Keyword arguments forwarded to ``func``.

        Note:
            ``key`` is reserved: it is consumed as the task label and is NOT
            forwarded to ``func``. If your function needs a parameter literally
            named ``key``, use ``add_function(func, kwargs={"key": ...}, key=label)``
            or ``add_task`` instead.
        """
        key = kwargs.pop("key", None)
        self._add_task(func, args, kwargs, label=key)

    def add_work(self, workload):
        """
        Adds multiple tasks to the runner from a list of tuples.

        Args:
            workload (list of tuple): Each tuple can be:
                - (func,)
                - (func, args)
                - (func, args, kwargs)
                - (func, args, kwargs, label)
        """

        for i, work in enumerate(workload):
            if not isinstance(work, tuple):
                raise TypeError(f"Workload item at index {i} is not a tuple")

            if len(work) < 1 or len(work) > 4:
                raise ValueError(
                    f"Invalid workload item at index {i}: expected a tuple with 1 to 4 elements in the format:\n"
                    f"(function: callable, args: tuple, kwargs: dict, label: str)\n"
                    f"But got {len(work)} element(s): {work}"
                )

            func = work[0]
            args = work[1] if len(work) > 1 else ()
            kwargs = work[2] if len(work) > 2 else {}
            label = work[3] if len(work) > 3 else None

            if not isinstance(args, Iterable):
                raise TypeError(
                    f"Workload item at index {i}: 'args' must be an iterable such as a tuple "
                    f"or list, got {type(args).__name__}. Did you mean ({func.__name__ if callable(func) else func!r}, ({args!r},))?"
                )
            if not isinstance(kwargs, Mapping):
                raise TypeError(
                    f"Workload item at index {i}: 'kwargs' must be a mapping such as a dict, "
                    f"got {type(kwargs).__name__}."
                )

            self._add_task(func, args, kwargs, label=label)

    def add_function(self, func, args=None, kwargs=None, key=None, log_exception=True, depends_on=None):
        """
        Adds a single function to the task runner.

        Args:
            func (callable): The function to be executed.
            args (tuple, optional): Positional arguments for the function.
            kwargs (dict, optional): Keyword arguments for the function.
            key (str, optional): Unique label for the task. If None, task ID will be used.
            log_exception (bool): Whether to log exceptions if task fails. (Unused, kept for backward compatibility of old library)
            depends_on (list, optional): Labels this task depends on.
        """

        args = args or ()
        kwargs = kwargs or {}
        self._add_task(func, args, kwargs, label=key, depends_on=depends_on)

    def execute_in_background(self):
        """
        Start the task execution in the background on a separate thread.

        This method starts a new thread to handle tasks in the background while 
        allowing the main thread to continue.
        """

        if self._has_started:
            raise RuntimeError("TaskRunner has already started execution. "
                               "Create a new TaskRunner instance to add tasks and run again.")
        self._validate_dependency_labels()
        self._has_started = True
        self.time_started = datetime.now()
        self._start_new_tasks()
        self._task_handler = threading.Thread(target=self._handle_tasks)
        self._task_handler.daemon = True
        self._task_handler._state = self.STATE_RUNNING
        self._task_handler.start()

    def get_background_results(self, verify=True, raise_exception=False, error_message=None):
        """
        Retrieve the results of the tasks after execution completes.

        Args:
            verify (bool): Whether to verify the task results.
            raise_exception (bool): Whether to raise an exception if errors are found.
            error_message (str): Custom error message to include in the exception.

        Returns:
            dict: A dictionary of task results.
        """
        self._task_handler._state = self.STATE_CLOSING
        self._task_handler.join()

        output = dict(self.results_registry)
        if verify:
            self.verify(raise_exception, error_message)
        return output

    def run(self, verify=True, raise_exception=False, error_message=None):
        """
        Execute the tasks and wait for results.

        This method executes the tasks, waits for completion, and returns the results.

        Args:
            verify (bool): Whether to verify the task results.
            raise_exception (bool): Whether to raise an exception if errors are found.
            error_message (str): Custom error message to include in the exception.

        Returns:
            dict: A dictionary of task results.
        """

        self.execute_in_background()
        return self.get_background_results(verify, raise_exception, error_message)

    def execute(self, verify=True, raise_exception=False, error_message=None):
        return self.run(verify=verify, raise_exception=raise_exception, error_message=error_message)

    def show_progress(self):
        """
        Display the progress of task execution in a human-readable format.
        
        Logs the progress of the tasks, showing the number of tasks completed 
        and the total number of tasks, along with the time elapsed.
        """
        time_taken = round((datetime.now() - self.time_started).total_seconds(), 2)
        minutes, seconds = divmod(time_taken, 60)
        time_display = f"{int(minutes)} min {round(seconds, 2)} sec"
        progress = round(self._executed_tasks/self._total_tasks * 100, 2)
        status = f"[{'#' * round(progress/4)}{'.' * (25 - round(progress/4))}]"
        progress = f"{status} {self._executed_tasks}/{self._total_tasks} [{progress}%]"
        self.log.info(f"{self.name} progress: {progress} in {time_display}")

    def is_running(self):
        """
        Check if the task execution is still in progress.

        Returns:
            bool: True if the tasks are still running, False otherwise.
        """
        return bool(self._task_handler and self._task_handler._state == self.STATE_RUNNING)
    
    def abort(self):
        """
        Abort the execution of tasks and terminate all running tasks.

        Returns:
            dict: A dictionary of task results, including any errors encountered.
        """
        self._terminate_tasks()
        self._task_handler = None
        self.verify()
        return dict(self.results_registry)

    def verify(self, raise_exception=False, error_message=None):
        """
        Verify that all tasks have completed successfully.

        Args:
            raise_exception (bool): Whether to raise an exception if errors are found.
            error_message (str): Custom error message to include in the exception.
        """
        error_message = error_message or "Execution Failed"
        if self.is_running():
            raise Exception("Execution is still in progress")
        
        headers = ['label', 'task', 'status', 'duration']
        rows = list()
        errors = list()
        for label, output in self.results_registry.items():
            rows.append([label, output['task_name'], output['status'], output['duration']])
            if output['has_failed']:
                errors.append(f"Task '{label}' failed with error: {output['error']} \n {output['trace']}")

        report = tabulate(rows, headers=headers, tablefmt='psql')
        
        if errors:
            error_msg = f"{error_message}\n{report}\n"+ '\n'.join(errors)
            if raise_exception:
                raise Exception(error_msg)
            else:
                self.log.error(error_msg)
        else:
            self.log.info(f"\n{report}")

    def _cleanup_finished_tasks(self):
        """
        Clean up completed tasks from the active list and invoke callback for each.

        Returns:
            bool: False if fail-fast condition was met, else True.
        """

        cleanup_done = False
        with self._state_lock:
            for idx in reversed(range(len(self.started_tasks))):
                task = self.started_tasks[idx]
                if self._has_task_timed_out(task):
                    # Terminate and join first to give the worker a chance to die
                    # before we record. Result integrity itself is guaranteed by
                    # the termination guard in TaskExecutor._record_results, which
                    # stops a lingering worker (thread or process) from overwriting
                    # the "Terminated" result afterwards.
                    task.terminate()
                    if task.executor:
                        task.executor.join(timeout=self.SHUTDOWN_GRACE)
                    task.update_results_on_termination(
                        TimeoutError(f"Task exceeded timeout of {self.timeout} seconds"))
                    cleanup_done = True
                    del self.started_tasks[idx]

                    self._executed_tasks += 1
                    self._failed_tasks.add(task.label)
                    self._terminated_tasks.add(task.label)
                    self._log_progress_if_due()

                    if self.log_errors or self.fast_fail:
                        self.log.error(f"Task '{task.label}' exceeded timeout of {self.timeout} seconds\n")
                    if self.fast_fail:
                        self.log.error("terminating execution!")
                        self._terminate_tasks()
                        return False

                elif task.exitcode is not None:
                    task.executor.join(timeout=self.SHUTDOWN_GRACE)
                    cleanup_done = True
                    del self.started_tasks[idx]

                    self._executed_tasks += 1
                    self._log_progress_if_due()

                    if task.has_failed:
                        self._failed_tasks.add(task.label)
                        exception = self.results_registry[task.label]['error']
                        trace_back = self.results_registry[task.label]['trace']
                        if self.log_errors or self.fast_fail:
                            self.log.error(f"{exception} {trace_back}\n")
                        if self.fast_fail:
                            self.log.error("terminating execution!")
                            self._terminate_tasks()
                            return False
                    else:
                        self._successful_tasks.add(task.label)

        return cleanup_done

    def _log_progress_if_due(self):
        """Emit a progress line at most once per PROGRESS_LOG_DIVISOR chunk."""
        if not self.progress_stats or not self._total_tasks:
            return
        step = max(1, self._total_tasks // self.PROGRESS_LOG_DIVISOR)
        if self._executed_tasks % step == 0:
            self.show_progress()

    def _start_new_tasks(self):
        """
        Start new tasks if there is available capacity for additional workers.
        """
        with self._state_lock:
            if self._terminating:
                return
            for _ in range(self.max_concurrency - len(self.started_tasks)):
                if not self.tasks:
                    return
                task = self.get_next_runnable_task()
                if not task:
                    return
                if not self._prepare_task_for_execution(task):
                    self._executed_tasks += 1
                    self._failed_tasks.add(task.label)
                    self._log_progress_if_due()
                    if self.fast_fail:
                        self.log.error("terminating execution!")
                        self._terminate_tasks()
                        return
                    continue
                try:
                    task.start()
                except Exception as exc:
                    self._record_start_failure(task, exc)
                    if self.fast_fail:
                        self.log.error("terminating execution!")
                        self._terminate_tasks()
                        return
                    continue
                self.started_tasks.append(task)

    def _prepare_task_for_execution(self, task):
        if not task.use_multiprocessing:
            return True

        pickling_error = self._get_pickling_error(task)
        if pickling_error is None:
            return True

        if self.fallback_to_thread_on_pickle_error:
            warning = "Task was not picklable; ran in thread fallback"
            task.use_thread_fallback(warning)
            self.log.warning(f"Task '{task.label}' was not picklable; running in thread fallback")
            return True

        task.update_results_on_failure(
            pickling_error,
            warning="Task was not picklable and thread fallback is disabled",
            execution_mode=None
        )
        return False

    @staticmethod
    def _get_pickling_error(task):
        try:
            ForkingPickler.dumps((
                task.label,
                task.task_handler.task,
                task.task_handler.args,
                task.task_handler.kwargs
            ))
        except Exception as exc:
            return exc
        return None

    def _record_start_failure(self, task, error):
        task.update_results_on_failure(error)
        self._executed_tasks += 1
        self._failed_tasks.add(task.label)
        self._log_progress_if_due()
 
    def _handle_tasks(self):
        """
        Manage and maintain the task execution process in the background.

        This method runs in a separate thread and checks the status of tasks, cleaning up 
        finished tasks and starting new ones as needed.
        """

        thread = threading.current_thread()

        while thread._state == self.STATE_RUNNING or (self.started_tasks and thread._state != self.STATE_TERMINATED):
            if self._cleanup_finished_tasks():
                self._start_new_tasks()
            time.sleep(self.MAINTENANCE_INTERVAL)

        if thread._state == self.STATE_TERMINATED and self.started_tasks:
            with self._state_lock:
                for i in reversed(range(len(self.started_tasks))):
                    task = self.started_tasks[i]
                    if not task.is_results_updated():
                        task.update_results_on_termination(
                            RuntimeError("Execution terminated before completion"))
                    self._executed_tasks += 1
                    self._terminated_tasks.add(task.label)
                    self.log.info(f"Deleting terminated task: {task.label}, {task.task_name}")
                    del self.started_tasks[i]

    def _terminate_tasks(self):
        """
        Terminate all tasks that are still running.

        This method forces the termination of tasks and ensures that results are updated.
        """

        with self._state_lock:
            self._terminating = True
            if self._task_handler:
                self._task_handler._state = self.STATE_TERMINATED

            for task in self.started_tasks + self.tasks:
                if task.exitcode is None:
                    task.terminate()
                if not task.is_results_updated():
                    task.update_results_on_termination(
                        RuntimeError("Execution terminated before completion"))
                    self._terminated_tasks.add(task.label)

    def _has_task_timed_out(self, task):
        if self.timeout is None or not task.is_running() or not task.time_started:
            return False
        return (datetime.now() - task.time_started).total_seconds() >= self.timeout

    def get_active_runner_count(self):
        """
        Returns the number of currently running task executors.

        Returns:
            int: Count of active/running tasks.
        """
        return sum(1 for task in self.started_tasks if task.is_running())

    def get_next_runnable_task(self):
        i = 0
        while i < len(self.tasks):
            task = self.tasks[i]
            task.depends_on -= self._successful_tasks

            blocking = [dep for dep in task.depends_on
                        if dep in self._failed_tasks or dep in self._terminated_tasks]
            if blocking:
                task.update_results_on_termination(
                    RuntimeError(f"Skipped: dependency {sorted(blocking, key=str)} failed or was terminated"))
                self._terminated_tasks.add(task.label)
                self._executed_tasks += 1
                self.tasks.pop(i)
                continue

            if not task.depends_on:
                return self.tasks.pop(i)

            i += 1
        return None

    def _validate_dependency_labels(self):
        known_labels = set(self.parents_of_label)
        missing_dependencies = {
            label: dependencies - known_labels
            for label, dependencies in self.parents_of_label.items()
            if dependencies - known_labels
        }
        if missing_dependencies:
            details = ", ".join(
                f"{label} depends on {sorted(dependencies, key=str)}"
                for label, dependencies in missing_dependencies.items()
            )
            raise ValueError(f"Unknown task dependency label(s): {details}.")

    def _find_cycle_from_new_task(self, label, depends_on):
        path = [label]
        visited = set()

        def visit(dependency):
            if dependency == label:
                return path + [label]
            if dependency in visited:
                return None

            visited.add(dependency)
            path.append(dependency)
            for parent_dependency in self.parents_of_label.get(dependency, set()):
                cycle = visit(parent_dependency)
                if cycle:
                    return cycle
            path.pop()
            return None

        for dependency in depends_on:
            cycle = visit(dependency)
            if cycle:
                return cycle
        return None
