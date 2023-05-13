"""
Unit tests for the backend logic of the web services application
"""
from sys import stderr
from os import sep, makedirs
from os.path import dirname, abspath
from typing import Optional

from time import sleep

import logging

from sri_testing.translator.sri.testing.processor import (
    CMD_DELIMITER,
    PWD_CMD,
    PYTHON_PATH,
    WorkerTask,
    PERCENTAGE_COMPLETION_SUFFIX_PATTERN
)
from tests.onehop import ONEHOP_TEST_DIRECTORY

logger = logging.getLogger()

TEST_RESULTS_PATH = abspath(f"{dirname(__file__)}{sep}test_results")
makedirs(TEST_RESULTS_PATH, exist_ok=True)


def _report_outcome(
        test_name: str,
        command_line: str,
        timeout: Optional[int] = 10,  # default to 10 seconds
        expecting_output: bool = True,
        expected_output: Optional[str] = None
):
    wp = WorkerTask(identifier=test_name, timeout=timeout)

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

    wp.close()


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


MOCK_WORKER = abspath(dirname(__file__)+sep+"mock_worker.py")


def test_progress_monitoring():

    wp = WorkerTask(identifier="test_progress_monitoring", timeout=1)

    wp.run_command(f"{PYTHON_PATH} {MOCK_WORKER}")

    done: bool = False
    percentage_completion: str = "0"
    tries: int = 0

    while not done:

        print("\nChecking progress...", file=stderr)
        sleep(1)

        next_pc: Optional[str] = None
        for line in wp.get_output():
            pc = PERCENTAGE_COMPLETION_SUFFIX_PATTERN.search(line)
            if pc and pc.group():
                next_pc = pc["percentage_completion"]

        if next_pc:
            tries = 0
            percentage_completion = next_pc
            print(f"{next_pc}% complete!", file=stderr)
        else:
            print("get_output() operation timed out?", file=stderr)
            tries += 1
            if tries > 10:
                assert False, "Progress monitoring timed out?"

        if percentage_completion == "100":
            done = True

    print("test_progress_monitoring() test completed successfully!", file=stderr)
