"""
Unit tests for the backend logic of the web services application
"""
import sys
from sys import stderr
from typing import Optional, Callable
import logging

from translator.sri.testing.processor import (
    CMD_DELIMITER,
    PWD_CMD,
    PYTHON_PATH,
    WorkerProcess
)
from tests.onehop import ONEHOP_TEST_DIRECTORY

logger = logging.getLogger()


def _report_outcome(
        test_name: str,
        command_line: str,
        timeout: Optional[int] = None,
        expecting_output: bool = True,
        expected_output: Optional[str] = None
):
    wp = WorkerProcess(timeout)
    wp.run_command(command_line)
    line: str

    if expecting_output:
        print(f"{test_name}() output: ...\n", file=stderr)

    for line in wp.get_output():
        if expecting_output:
            assert line, f"{test_name}() is missing Worker Process output?"
            msg = '\n'.join(line.split('\r\n'))
            print(f"\t{msg}", file=stderr)
            if expected_output:
                # Strip leading and training whitespace of the report for the comparison
                assert line.strip() == expected_output
        else:
            assert not line, f"{test_name}() has unexpected non-empty Worker Process output: {line}?"

    if expecting_output:
        print("\n...Done!", file=stderr)


def test_run_command():
    _report_outcome("test_run_command", f"dir .* {CMD_DELIMITER} {PYTHON_PATH} --version")


def test_cd_path():
    _report_outcome(
        "test_cd_path", f"cd {ONEHOP_TEST_DIRECTORY} {CMD_DELIMITER} {PWD_CMD}",
        expected_output=ONEHOP_TEST_DIRECTORY
    )


def test_run_pytest_command():
    _report_outcome("test_run_pytest_command", f"cd {ONEHOP_TEST_DIRECTORY} {CMD_DELIMITER} pytest --version")


def test_run_process_timeout():
    # one second timeout, very short relative to
    # the runtime of the specified command line
    _report_outcome(
        "test_run_process_timeout",
        f'{PYTHON_PATH} -c "from time import sleep; sleep(2)"',
        timeout=1,
        expecting_output=False
    )


# TODO: need to design a unit test for WorkerProcess process monitoring?
def test_progress_monitoring():
    _report_outcome(
        "test_progress_monitoring",
        f'{PYTHON_PATH} -c "for i in range(20): print(i)"'
    )
