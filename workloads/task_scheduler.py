from queue import Queue
from dataclasses import dataclass
from typing import Any, Callable
import uuid
import time
import threading
from datetime import datetime, timedelta
from enum import Enum


@dataclass
class Task:
    id: str
    func: Callable
    args: tuple
    kwargs: dict
    timeout: int  # timeout in seconds
    created_at: datetime
    max_retry: int = 0
    current_retry: int = 0

    @classmethod
    def create(
        cls, func: Callable, timeout: int, max_retry: int = 0, *args, **kwargs
    ) -> "Task":
        return cls(
            id=str(uuid.uuid4()),
            func=func,
            args=args,
            kwargs=kwargs,
            timeout=timeout,
            created_at=datetime.now(),
            max_retry=max_retry,
            current_retry=0,
        )


class TaskStatus(Enum):
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    FINISHED = "FINISHED"
    FAILED = "FAILED"
    NOT_FOUND = "NOT_FOUND"


@dataclass
class TaskResult:
    task_id: str
    status: TaskStatus
    output: Any = None
    position: int = 0
    err_message: str = ""


class TaskScheduler:
    def __init__(self):
        self.task_queue = Queue()
        self.current_task: Task | None = None
        self.running = False
        self._lock = threading.Lock()
        self.task_results = {}  # Store task results

    def add_task(
        self, func: Callable, timeout: int, max_retry: int = 0, *args, **kwargs
    ) -> str:
        """Add a task to the queue and return its ID"""
        task = Task.create(func, timeout, max_retry, *args, **kwargs)
        self.task_queue.put(task)
        return task.id

    def start(self):
        """Start the scheduler"""
        if self.running:
            return
        self.running = True
        self._process_tasks()

    def stop(self):
        """Stop the scheduler"""
        self.running = False

    def _process_tasks(self):
        """Main task processing loop"""
        while self.running:
            if not self.task_queue.empty():
                with self._lock:
                    self.current_task = self.task_queue.get()
                    if not self.current_task:
                        continue

                    position = self.task_queue.qsize()
                    self.task_results[self.current_task.id] = TaskResult(
                        task_id=self.current_task.id,
                        status=TaskStatus.IN_PROGRESS,
                        position=position,
                    )

                try:
                    # Create a timer for timeout
                    timer = threading.Timer(
                        self.current_task.timeout,
                        self._handle_timeout,
                        args=[self.current_task.id],
                    )
                    timer.start()

                    # Execute the task
                    result = self.current_task.func(
                        *self.current_task.args, **self.current_task.kwargs
                    )

                    # Cancel timer if task completed successfully
                    timer.cancel()

                    # Update task result
                    self.task_results[self.current_task.id] = TaskResult(
                        task_id=self.current_task.id,
                        status=TaskStatus.FINISHED,
                        output=result,
                        position=0,
                    )

                except Exception as e:
                    should_retry = (
                        self.current_task.current_retry < self.current_task.max_retry
                    )

                    if should_retry:
                        # Increment retry counter and requeue
                        self.current_task.current_retry += 1
                        print(
                            f"Retrying task {self.current_task.id} (attempt {self.current_task.current_retry}/{self.current_task.max_retry})"
                        )
                        self.task_queue.put(self.current_task)

                        self.task_results[self.current_task.id] = TaskResult(
                            task_id=self.current_task.id,
                            status=TaskStatus.QUEUED,
                            output=f"Retry attempt {self.current_task.current_retry}",
                            position=self.task_queue.qsize(),
                        )
                    else:
                        self.task_results[self.current_task.id] = TaskResult(
                            task_id=self.current_task.id,
                            status=TaskStatus.FAILED,
                            output=f"Failed after {self.current_task.current_retry} retries: {str(e)}",
                            position=0,
                        )
                        print(
                            f"Task {self.current_task.id} failed permanently: {str(e)}"
                        )
                finally:
                    with self._lock:
                        self.current_task = None

            time.sleep(0.3)

    def _handle_timeout(self, task_id: str):
        """Handle task timeout"""
        with self._lock:
            if self.current_task and self.current_task.id == task_id:
                should_retry = (
                    self.current_task.current_retry < self.current_task.max_retry
                )

                if should_retry:
                    self.current_task.current_retry += 1
                    print(
                        f"Retrying task {task_id} after timeout (attempt {self.current_task.current_retry}/{self.current_task.max_retry})"
                    )
                    self.task_queue.put(self.current_task)

                    self.task_results[task_id] = TaskResult(
                        task_id=task_id,
                        status=TaskStatus.QUEUED,
                        output=f"Retry attempt {self.current_task.current_retry} after timeout",
                        position=self.task_queue.qsize(),
                    )
                else:
                    self.task_results[task_id] = TaskResult(
                        task_id=task_id,
                        status=TaskStatus.FAILED,
                        output=f"Task timed out permanently after {self.current_task.current_retry} retries",
                        position=0,
                    )
                    print(
                        f"Task {task_id} timed out permanently after {self.current_task.timeout} seconds"
                    )

                self.current_task = None

    def get_current_task_id(self) -> str | None:
        """Return the current running task ID if any"""
        return self.current_task.id if self.current_task else None

    def get_task_result(self, task_id: str) -> TaskResult:
        """Get the result of a task by its ID"""
        return self.task_results.get(
            task_id, TaskResult(task_id=task_id, status=TaskStatus.NOT_FOUND)
        )
