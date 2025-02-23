import unittest
import time
import threading
from datetime import datetime
from unittest.mock import MagicMock
from workloads.task_scheduler import TaskScheduler, Task, TaskStatus, TaskResult


class TestTaskScheduler(unittest.TestCase):
    def setUp(self):
        """Set up a test instance of the scheduler."""
        self.scheduler = TaskScheduler()
        scheduler_thread = threading.Thread(target=self.scheduler.start, daemon=True)
        scheduler_thread.start()

    def tearDown(self):
        """Clean up after each test."""
        self.scheduler.reset()
        time.sleep(0.1)  # Allow scheduler to stop

    def test_add_task(self):
        """Test adding a task returns a valid task ID."""

        def dummy_func():
            pass

        task_id = self.scheduler.add_task(dummy_func, timeout=10)
        self.assertIsInstance(task_id, str)
        self.assertTrue(len(task_id) > 0)

    def test_task_execution_success(self):
        """Test successful task execution."""
        result_value = "success"

        def test_func():
            return result_value

        task_id = self.scheduler.add_task(test_func, timeout=5)
        time.sleep(1)  # Allow task to process

        result = self.scheduler.get_task_result(task_id)
        self.assertEqual(result.status, TaskStatus.FINISHED)
        self.assertEqual(result.output, result_value)
        self.assertEqual(result.position, 0)

    def test_task_execution_failure(self):
        """Test task execution failure and retry mechanism."""

        def failing_func():
            raise ValueError("Test error")

        task_id = self.scheduler.add_task(failing_func, timeout=5, max_retry=2)
        time.sleep(3)  # Allow for retries

        result = self.scheduler.get_task_result(task_id)
        self.assertEqual(result.status, TaskStatus.FAILED)
        self.assertTrue("Failed after 2 retries" in str(result.output))

    def test_task_timeout(self):
        """Test task timeout handling."""

        def slow_func():
            time.sleep(5)
            return "done"

        task_id = self.scheduler.add_task(slow_func, timeout=1, max_retry=0)
        time.sleep(3)  # Allow for timeout

        result = self.scheduler.get_task_result(task_id)
        self.assertEqual(result.status, TaskStatus.FAILED)
        self.assertTrue("timed out permanently" in str(result.output))

    def test_get_nonexistent_task_result(self):
        """Test getting result of a nonexistent task."""
        result = self.scheduler.get_task_result("nonexistent-id")
        self.assertEqual(result.status, TaskStatus.NOT_FOUND)

    def test_task_with_arguments(self):
        """Test task execution with arguments."""

        def add_numbers(a, b, c=0):
            return a + b + c

        task_id = self.scheduler.add_task(add_numbers, 5, 0, 1, 2, c=3)
        time.sleep(0.5)

        result = self.scheduler.get_task_result(task_id)
        self.assertEqual(result.status, TaskStatus.FINISHED)
        self.assertEqual(result.output, 6)

    def test_multiple_tasks_queue(self):
        """Test multiple tasks are processed in order."""
        results = []

        def append_number(n):
            results.append(n)
            return n

        task_ids = []
        for i in range(3):
            task_id = self.scheduler.add_task(append_number, 5, 0, i)
            task_ids.append(task_id)

        time.sleep(1)  # Allow all tasks to complete

        self.assertEqual(results, [0, 1, 2])
        for task_id in task_ids:
            result = self.scheduler.get_task_result(task_id)
            self.assertEqual(result.status, TaskStatus.FINISHED)

    def test_get_current_task_id(self):
        """Test getting current task ID."""

        def slow_task():
            time.sleep(2)
            return "done"

        task_id = self.scheduler.add_task(slow_task, 5)
        time.sleep(0.5)
        current_task_id = self.scheduler.get_current_task_id()

        self.assertEqual(current_task_id, task_id)


if __name__ == "__main__":
    unittest.main()
