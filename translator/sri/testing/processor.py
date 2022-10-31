"""
Utility module to support SRI Testing harness background processing

The module launches the SRT Testing test harness using the Python 'multiprocessor' library.
See https://docs.python.org/3/library/multiprocessing.html?highlight=multiprocessing for details.
"""
from threading import Event
from typing import Optional, Generator

from sys import platform, executable, stderr
from os import getpid, getppid

from re import compile
from time import sleep
from queue import Empty

from multiprocessing import Process, Pipe, Lock, Queue, get_context
from multiprocessing.context import BaseContext
from multiprocessing.connection import Connection

from subprocess import Popen, PIPE, STDOUT

import logging

from translator.sri.testing.report_db import (
    TestReportDatabase,
    get_test_report_database, TestReport
)

logger = logging.getLogger()


if platform == "win32":
    # Windoze
    CMD_DELIMITER = "&&"
    PWD_CMD = "cd"
    from pathlib import PureWindowsPath
    PYTHON_PATH = PureWindowsPath(executable).as_posix()
elif platform in ["linux", "linux1", "linux2", "darwin"]:
    # *nix
    CMD_DELIMITER = ";"
    PWD_CMD = "pwd"
    PYTHON_PATH = executable
else:
    print(f"Warning: other OS platform '{platform}' encountered?")
    CMD_DELIMITER = ";"
    PWD_CMD = "pwd"
    PYTHON_PATH = executable

_test_report_database: TestReportDatabase = get_test_report_database()

PERCENTAGE_COMPLETION_SUFFIX_PATTERN = compile(r"(\[\s*(?P<percentage_completion>\d+)%])?$")


def _progress_monitor(line: str) -> Optional[str]:
    logger.debug(f"Pytest output: {line}")
    pc = PERCENTAGE_COMPLETION_SUFFIX_PATTERN.search(line)
    if pc and pc.group():
        return pc["percentage_completion"]
    else:
        return None


def _worker_process(
        identifier: str,
        pipe: Pipe,
        lock: Lock,
        queue: Queue,
        termination: Event,
        command_line: str
):
    """
    Wrapper for a background worker process which runs a specified command.

    :param identifier: str, worker process identifier, used to configure logging
    :param pipe: Pipe, process pipe between the Worker and caller
    :param lock: Lock, process lock used to synchronize background output
    :param queue: Queue, used for communication of worker process to caller
    :param termination: Event, used for signal early process termination
    :param command_line: str, the worker process command to execute

    :return: None (process state indirectly returned via Queue)
    """
    lock.acquire()
    try:
        print('Module:', __name__, flush=True, file=stderr)
        print('Parent process:', getppid(), flush=True, file=stderr)
        process_id: int = getpid()
        print(f"Background process id: {process_id}", flush=True, file=stderr)
        msg: str = f'Executing Test Harness command "{command_line}"'
        print(msg, flush=True, file=stderr)
    finally:
        lock.release()

    # send the child process ID back to
    # the caller, as a point of reference
    queue.put(process_id)

    return_code: int
    return_status: str

    report: TestReport = _test_report_database.get_test_report(identifier)
    report.open_logger()

    previous_percentage_complete: int = 0
    sequential_progress: int = 0

    try:
        with Popen(
                args=command_line,
                shell=True,
                bufsize=1,
                universal_newlines=True,
                stdout=PIPE,
                stderr=STDOUT
        ) as proc:
            for line in proc.stdout:
                end_early: bool
                lock.acquire()
                try:
                    # We check here if the main process wants us
                    # to prematurely terminate the Worker process.
                    end_early = termination.is_set()
                finally:
                    lock.release()

                if end_early:
                    proc.terminate()
                    break

                # Echo 'line' to report log
                report.write_logger(line)
                line = line.strip()
                if line:
                    # Simple-minded strategy of "just-in-time" processing of
                    # progress_monitoring of percentage completion parsed out
                    percentage_complete: Optional[str] = _progress_monitor(line)
                    if percentage_complete is not None:
                        if int(percentage_complete) > previous_percentage_complete:
                            previous_percentage_complete = int(percentage_complete)
                            sequential_progress = 0
                        else:
                            # add synthetic progress inside the 1 % increases
                            # reported back by the Pytest background process
                            sequential_progress += 1

                        # synthesize a float progress value that is
                        # a hybrid of percentage and sequential progress
                        overall_progress = float(f"{str(previous_percentage_complete)}.{str(sequential_progress)}")
                        pipe.send(round(overall_progress, 4))

                        # sleep briefly to temporarily
                        # relinquish control to other threads
                        sleep(0.01)

            return_code = proc.wait()

        return_status = "Worker Task Completed?"

    except RuntimeError as rte:
        logger.error(f"run_script({command_line}) exception: {str(rte)}")
        return_code = 1
        return_status = f"Worker Task Exception: {str(rte)}?"

    finally:
        report.close_logger()

    # propagate the result - successful or not - back to the caller
    queue.put(f"{WorkerTask.COMPLETED} - Return Code: {return_code}\nStatus {return_status}")


class WorkerProcessException(Exception):
    pass


class WorkerTask:

    def __init__(self, identifier: Optional[str] = None, timeout: Optional[int] = None):
        """
        Constructor for WorkerProcess.

        :param identifier: str, worker process identifier, used to tag the process log
        :param timeout: int, worker process data query access timeout (Default: None => queue data access is blocking?)
        """
        self._identifier: str = identifier if identifier else "Anonymous_Worker_Process"
        self._timeout: Optional[int] = timeout

        self._parent_conn: Optional[Connection] = None
        self._child_conn: Optional[Connection] = None
        self._ctx: BaseContext = get_context('spawn')
        self._lock = self._ctx.Lock()
        self._queue = self._ctx.Queue()
        self._termination = self._ctx.Event()
        self._process: Optional[Process] = None
        self._process_id: int = 0
        self._status: Optional[str] = None

    def run_command(self, command_line: str):
        """
        Run a provided command line string, as a background process.

        :param command_line: str, command line string to run as a shell command in a background worker process.
        """
        assert command_line  # should not be empty?

        logger.debug(f"run_command() command: {command_line}")
        
        # TODO: perhaps replace this embedded processing code with a FIFO job Queue
        #       to allow for disciplined processing of multiple (sequential) test_runs
        # TODO: may need to manage several worker processes, therefore, may need to use multiprocessing Pools? see
        #       https://docs.python.org/3/library/multiprocessing.html?highlight=multiprocessing#module-multiprocessing
        try:
            # Sanity check: Work Process is a singleton?
            assert not self._process

            # Directly access the internal Worker Task task
            # standard output/error, using an interprocess Pipe
            self._parent_conn, self._child_conn = Pipe()

            self._process = self._ctx.Process(
                target=_worker_process,
                args=(
                    self._identifier,
                    self._child_conn,
                    self._lock,
                    self._queue,
                    self._termination,
                    command_line
                )
            )

            self._process.start()

            pid_tries: int = 10
            while not self._process_id and pid_tries:
                try:
                    self._process_id = self._queue.get(block=True, timeout=self._timeout)

                except Empty:

                    logger.debug("run_command() 'process_id' not available (yet) in the interprocess Queue?")
                    self._process_id = 0  # return a zero PID to signal 'Empty'?

                pid_tries -= 1

            # for some reason, the worker process didn't send back a
            # 'process_id', with queue access timeouts after several retries
            if not self._process_id:
                raise RuntimeError("Worker process startup time-out?")

            # TODO: perhaps I need to initiate a lightweight background thread *here*, to monitor the PIPE for
            #       Worker Task progress, instead of relying on access to PIPE output in the /status endpoint?

        except Exception as ex:

            logger.warning(f"run_command() command: '{command_line}' raised an exception: {str(ex)}?")
            self.terminate()

    def get_output(self, timeout: float = 1.0) -> Generator:
        if self._parent_conn:
            print("\n", file=stderr)
            while True:
                try:
                    if self._parent_conn.poll(timeout):
                        line = self._parent_conn.recv()
                        yield line
                    else:
                        # The Generator iteration is stopped if
                        # the get_output polling timeout is hit
                        return None
                except (EOFError, BrokenPipeError) as exc:
                    # The caller has to distinguish in
                    # between polling timeouts and output EOF
                    logger.debug(f"WorkerProcess.get_output(): {exc}")
                    return None
        else:
            # Caller also gets nothing if there is no active connection
            return None

    PENDING: str = "Worker Task Pending"
    NOT_RUNNING: str = "Worker Task Not Running"
    COMPLETED: str = "Worker Task Completed"
    RUNNING: str = "Worker Task Running"

    def status(self) -> str:

        if not self._status or self._status == self.RUNNING:

            # ... otherwise, check the process queue for a final message...
            try:
                self._status = self._queue.get(block=True, timeout=1)
            except Empty:
                # ... (hopefully) still running...
                self._status = self.RUNNING

            # Hacker assumption: that a missing process is one deemed "completed"
            if not (self._process and self._process.is_alive() and self._process_id):
                self._status = self.NOT_RUNNING

        return self._status

    def terminate(self) -> bool:
        if self.status() == self.RUNNING:
            self._lock.acquire()
            try:
                self._termination.set()
            finally:
                self._lock.release()

            self._process.join()
            self._process = None
            self._process_id = 0

        return True if self.status() == self.NOT_RUNNING else False

    def close(self):
        # Job done, the parent, not the child, sets the connections to None
        # which closes the interprocess pipe, when ready?
        self._parent_conn = None
        self._child_conn = None
        if self._process:
            self._process.join()
            self._process = None
            self._process_id = 0
