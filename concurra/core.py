import os
import time
import traceback
import threading
import multiprocessing
import logging
from datetime import datetime
from tabulate import tabulate

LOGGER = logging.getLogger(__name__)


class TaskExecutor:
    """
    class for executing tasks while recording runtime results and statistics.
    """

    def __init__(self, task_handler, task_id, label, results_registry, use_multiprocessing=False):
        """
        Initialize the executor.

        Args:
            task_handler: The object that defines a `.run()` method for the task.
            task_id: Unique identifier for the task execution.
            label: Key used to store results in the results_registry.
            results_registry: Dictionary to store execution metadata and results.
        """

        self.task_handler = task_handler
        self.task_name = task_handler.name
        self.task_id = task_id
        self.label = label
        self.results_registry = results_registry
        self.executor = None
        self.time_started = None
        self.time_finished = None
        self._has_started = False
        self._init_results_registry()
        self.use_multiprocessing = use_multiprocessing

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
        else:
            self.executor = threading.Thread(target=self.run)
        
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
        return f"<TaskRunner: {self.name}>"


class TaskRunner:

    STATE_RUNNING = 0
    STATE_CLOSING = 1
    STATE_TERMINATED = 2
    MAINTENANCE_INTERVAL = 0.1  # seconds
    PROGRESS_LOG_DIVISOR = 10   # log progress every (total_tasks / this)

    def __init__(self, max_concurrency=None, name=None, timeout=None, progress_stats=True, fast_fail=False, 
                 use_multiprocessing=False, logger=None, log_errors=False):
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
        """

        self.log = logger or LOGGER
        self.max_concurrency = max_concurrency or os.cpu_count()
        if self.max_concurrency < 1:
            self.log.warning("Max worker count is 1, task will not run in parallel")
            self.max_concurrency = 1
        self.timeout = timeout
        self.name = name or self.__class__.__name__
        self.progress_stats = progress_stats
        self.fast_fail = fast_fail
        self.use_multiprocessing = use_multiprocessing
        self.log_errors = log_errors

        if use_multiprocessing:
            manager = multiprocessing.Manager()
            self.results_registry = manager.dict()
        else:
            self.results_registry = dict()

        self.tasks = list()
        self.started_tasks = list()
        self.time_started = None
        
        self._task_handler = None
        self._total_tasks = 0
        self._executed_tasks = 0
        self._has_started = False

    def add_task(self, task, *args, label=None, **kwargs):
        """
        Add a task to the task queue to be executed.

        Args:
            task (callable): The function or task handler to execute.
            *args: Arguments to pass to the task.
            label (str): Unique label for the task (default is the task ID).
            **kwargs: Additional keyword arguments for the task.
        """

        if self._has_started:
            raise RuntimeError("Cannot add tasks after execution has started.")
    
        if not callable(task):
            raise TypeError(f"The provided task '{task}' is not callable.")

        task_handler = TaskHandler(task, *args, **kwargs)
        task_id = len(self.tasks)
        label = label or task_id

        if label in (t.label for t in self.tasks):
            raise ValueError(f"Duplicate task label: '{label}' already exists.")

        task_executor = TaskExecutor(task_handler, task_id, label, self.results_registry,
                                     use_multiprocessing=self.use_multiprocessing)
        self.tasks.append(task_executor)
        self._total_tasks += 1

    def execute_in_background(self):
        """
        Start the task execution in the background on a separate thread.

        This method starts a new thread to handle tasks in the background while 
        allowing the main thread to continue.
        """

        if self._has_started:
            raise RuntimeError("TaskRunner has already started execution. "
                               "Create a new TaskRunner instance to add tasks and run again.")
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
        self._task_handler.join(timeout=self.timeout)
        self._terminate_tasks()

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
        return bool(self._task_handler and self._task_handler._state == 0)
    
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
        excution_type = 'multiprocessing' if self.use_multiprocessing else 'multithreading'
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
        for idx in reversed(range(len(self.started_tasks))):
            task = self.started_tasks[idx]
            if task.exitcode is not None:
                task.executor.join(timeout=self.timeout)
                cleanup_done = True
                del self.started_tasks[idx]

                self._executed_tasks += 1
                if self.progress_stats and self._executed_tasks % (self._total_tasks / self.PROGRESS_LOG_DIVISOR) < 1:
                    self.show_progress()

                if task.has_failed:
                    exception = self.results_registry[task.label]['error']
                    trace_back = self.results_registry[task.label]['trace']
                    if self.log_errors or self.fast_fail:
                        self.log.error(f"{exception} {trace_back}\n")
                    if self.fast_fail:
                        self.log.error(f"terminating execution !")
                        self._terminate_tasks()

                    return False

        return cleanup_done

    def _start_new_tasks(self):
        """
        Start new tasks if there is available capacity for additional workers.
        """
        for _ in range(self.max_concurrency - len(self.started_tasks)):
            if not self.tasks:
                return
            task = self.tasks.pop(0)
            task.start()
            self.started_tasks.append(task)
 
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
            for i in reversed(range(len(self.started_tasks))):
                task = self.started_tasks[i]
                if not task.is_results_updated():
                    task.update_results_on_termination()
                self.log.info(f"Deleting terminated task: {task.label}, {task.task_name}")
                del self.started_tasks[i]

    def _terminate_tasks(self):
        """
        Terminate all tasks that are still running.

        This method forces the termination of tasks and ensures that results are updated.
        """

        if not self.started_tasks:
            return

        self.timeout = 0.1
        self._task_handler._state = self.STATE_TERMINATED

        for task in self.started_tasks + self.tasks:
            if task.exitcode is None:
                task.terminate()
            if not task.is_results_updated():
                task.update_results_on_termination()
