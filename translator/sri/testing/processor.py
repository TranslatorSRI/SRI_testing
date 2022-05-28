"""
Utility module to support SRI Testing harness background processing

The module launches the SRT Testing test harness using the Python 'multiprocessor' library.
See https://docs.python.org/3/library/multiprocessing.html?highlight=multiprocessing for details.
"""
from multiprocessing import Process
from sys import platform, stdout, stderr
from encodings.utf_8 import decode
from queue import Empty
from typing import Optional, Union, Tuple
import multiprocessing as mp
from subprocess import run, CompletedProcess, CalledProcessError, TimeoutExpired
import os
import logging
logger = logging.getLogger()

#
# Application-specific parameters
#
DEFAULT_WORKER_TIMEOUT = 120  # 2 minutes?


if platform == "win32":
    # Windoze
    CMD_DELIMITER = "&&"
elif platform in ["linux1", "linux2", "darwin"]:
    # *nix
    CMD_DELIMITER = ";"
else:
    print(f"Warning: other OS platform '{platform}' encountered?")
    CMD_DELIMITER = ";"


def worker_process(lock: mp.Lock, queue: mp.Queue, command_line: str):
    """
    Wrapper for a background worker process which runs a specified command.

    :param lock: Lock, process lock used to synchronize background output
    :param queue: Queue, used for communication of worker process to caller
    :param command_line: str, the worker process command to execute
    :return:
    """
    lock.acquire()
    try:
        print('Module:', __name__, flush=True, file=stderr)
        print('Parent process:', os.getppid(), flush=True, file=stderr)
        process_id: int = os.getpid()
        print(f"Background process id: {process_id}", flush=True, file=stderr)
        msg: str = f'Executing Test Harness command "{command_line}"'
        print(msg, flush=True, file=stderr)
    finally:
        lock.release()

    # send the child process ID back to
    # the caller, as a point of reference
    queue.put(process_id)

    result: Union[CompletedProcess, CalledProcessError, TimeoutExpired]
    try:
        # do the heavy lifting here
        result = run(
            command_line,
            shell=True,
            check=True,
            capture_output=True,

            # running test harnesses may take a very long time
            # so maybe a bit challenge to set a sensible timeout here
            # timeout=100,
        )

    except CalledProcessError as cpe:
        result = cpe

    # except TimeoutExpired as toe:
    #     print(str(toe), flush=True, file=stderr)
    #     result = toe

    lock.acquire()
    try:
        print(f"Result: {str(result)}", flush=True, file=stderr)

        return_code = result.returncode
        print(f"Return Code: {return_code}", flush=True, file=stderr)

        output = result.stdout
        print(f"Output: {output}", flush=True, file=stdout)

        errors = result.stderr
        print(f"Errors: {errors}", flush=True, file=stderr)

    finally:
        lock.release()

    # propagate the result - successful or not - back to the caller
    queue.put(result)


def run_command(
        command_line: str
) -> Tuple[int, Optional[str]]:
    """
    Run a provided command line string, as a background process.

    :param command_line: str, command line string to run as a shell command in a background worker process.

    :return: Tuple[int, str], (process identifier, optional raw text standard output) for this background command.
             If process_identifier is zero, then the process is considered inaccessible; otherwise, the returned
             'process_id' may be used to track and access background worker process again in the future.
    """
    assert command_line  # should not be empty?

    logger.debug(f"run_test_harness() command: {command_line}")

    bg_process = Optional[Process]
    process_id: int = 0
    result: Optional[Union[CompletedProcess, CalledProcessError, TimeoutExpired, Empty]] = None
    report: Optional[str] = None

    # TODO: might need to manage several worker processes, therefore, may need to use multiprocessing Pools? see
    #       https://docs.python.org/3/library/multiprocessing.html?highlight=multiprocessing#module-multiprocessing
    try:
        # Get things started...
        ctx = mp.get_context('spawn')
        queue = ctx.Queue()
        lock = ctx.Lock()
        bg_process = ctx.Process(target=worker_process, args=(lock, queue, command_line))
        bg_process.start()

        pid_tries: int = 10
        while not process_id and pid_tries:
            try:
                process_id = queue.get(block=True, timeout=DEFAULT_WORKER_TIMEOUT)
            except Empty:
                logger.debug("run_test_harness() 'process_id' not available (yet) in the interprocess Queue?")
                process_id = 0  # return a zero PID to signal 'Empty'?
            pid_tries -= 1

        # for some reason, the worker process didn't send back
        # a 'process_id', after several retries with timeouts
        if not process_id:
            bg_process.kill()
            bg_process = None
            process_id = 0
            report = "Background process did not start up properly?"
        else:
            try:
                result = queue.get(block=True, timeout=DEFAULT_WORKER_TIMEOUT)
                logger.debug(f"run_test_harness() result:\n\t{result}")
            except Empty as empty:
                # TODO: something sensible here... maybe fall through and try again later in another handler call
                logger.debug("run_test_harness() 'result' not available (yet) in the interprocess Queue?")
                result = empty

    except Exception as ex:
        logger.warning(f"run_test_harness() command: '{command_line}' raised an exception: {str(ex)}?")
        if bg_process:
            bg_process.kill()
        process_id = 0
        result = None
        report = f"Background process start-up exception: {str(ex)}?"

    if result:
        if isinstance(result, CompletedProcess):
            report = decode(result.stdout)[0]  # sending back full raw process standard output
            if result.returncode != 0:
                report = f"Warning... Non-zero return code '{str(result.returncode)}': \n\t{report}"
            bg_process.join()
        elif isinstance(result, Empty):
            # test still running, bg_process likely still running and the 'process_id'
            # is likely (still) valid. Defer access to raw data output... try again later?
            pass
        elif isinstance(result, CalledProcessError):
            # process aborted by internal error?
            report = decode(result.stdout)[0]
            if bg_process:
                bg_process.kill()
            process_id = 0  # signal failed execution of worker process?
        elif isinstance(result, TimeoutExpired):
            # Indeterminate process state(?), 'process_id' may be unknown
            # but *maybe* try accessing background process again later?
            pass

    return process_id, report
