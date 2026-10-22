import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch


class BoundedRunnerTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / "scripts/run_tests.py"
        spec = importlib.util.spec_from_file_location("bounded_ci_tests", path)
        self.runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.runner)

    def test_timeout_bounds_refuse_invalid_limits_before_running(self):
        for timeout in (True, 0, 4, 1801, "600"):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                self.runner.run(unittest.TestSuite(), timeout)

    def test_success_and_failure_retain_the_actual_test_result_and_cancel_watchdog(self):
        for successful in (True, False):
            result = Mock()
            result.wasSuccessful.return_value = successful
            with patch.object(self.runner.faulthandler, "dump_traceback_later") as schedule, patch.object(self.runner.faulthandler, "cancel_dump_traceback_later") as cancel, patch.object(self.runner.unittest, "TextTestRunner") as factory:
                factory.return_value.run.return_value = result
                self.assertIs(self.runner.run(unittest.TestSuite(), 600), successful)
                self.assertTrue(schedule.call_args.kwargs["exit"])
                self.assertEqual(schedule.call_args.args, (600,))
                cancel.assert_called_once()

    def test_runner_exception_still_cancels_watchdog(self):
        with patch.object(self.runner.faulthandler, "dump_traceback_later"), patch.object(self.runner.faulthandler, "cancel_dump_traceback_later") as cancel, patch.object(self.runner.unittest, "TextTestRunner", side_effect=RuntimeError("test runner failure")):
            with self.assertRaises(RuntimeError):
                self.runner.run(unittest.TestSuite(), 600)
            cancel.assert_called_once()
