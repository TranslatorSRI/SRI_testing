"""
SRI Testing Report utility functions.
"""
from typing import Optional, Dict, Tuple, List, Generator
from datetime import datetime
import re

from translator.sri.testing.processor import CMD_DELIMITER, WorkerProcess

from tests.onehop import ONEHOP_TEST_DIRECTORY

from translator.sri.testing.report_db import (
    TestReport,
    TestReportDatabase,
    get_test_report_database
)

import logging
logger = logging.getLogger()
logger.setLevel("DEBUG")

#
# Application-specific parameters
#
DEFAULT_WORKER_TIMEOUT = 120  # 2 minutes for small PyTests?

#
# June/July 2022 - new reporting strategy, based on an exported
# summary, edge details and unit test TRAPI JSON files
#

UNIT_TEST_NAME_PATTERN = re.compile(
    r"^test_onehops.py:(\d+)?:(test_trapi_(?P<component>kp|ara)s|\s)(\[(?P<case>[^]]+)])"
)
TEST_CASE_PATTERN = re.compile(
    r"^(?P<resource_id>[^#]+)(#(?P<edge_num>\d+))?(-(?P<test_id>.+))?$"
)


def build_resource_key(component: str, ara_id: Optional[str], kp_id: str, target: Optional[str] = None) -> str:
    """
    Returns a key identifier ('path') to an test summary document of a given ARA and/or KP resource.

    :param component:
    :param ara_id: Optional[str], may be empty (if the resource is directly a KP)
    :param kp_id: str, should not be empty either when directly accessed or indirectly via an ARA
    :param target: Optional[str], if not empty, append to end of key path
    :return: str, resource-centric document key
    """
    resource_key: str = component
    resource_key += f"/{ara_id}" if ara_id else ""
    resource_key += f"/{kp_id}"

    if target:
        resource_key += f"/{target}"
    return resource_key


def build_resource_summary_key(component: str, ara_id: Optional[str], kp_id: str) -> str:
    """
    Returns a key identifier ('path') to an resource summary document of a given ARA and/or KP resource.

    :param component:
    :param ara_id:
    :param kp_id:
    :return: str, resource-centric document key
    """
    return build_resource_key(component, ara_id, kp_id, target="resource_summary")


def build_edge_details_key(component: str, ara_id: Optional[str], kp_id: str, edge_num: str) -> str:
    """
    Returns a key identifier ('path') to an edge details related document.

    :param component:
    :param ara_id:
    :param kp_id:
    :param edge_num:
    :return: str, edge-centric document key
    """
    return build_resource_key(component, ara_id, kp_id, target=f"{kp_id}-{edge_num}")


def build_recommendations_key(component: str, ara_id: Optional[str], kp_id: str) -> str:
    """
    Returns a key identifier ('path') to an resource recommendations document of a given ARA and/or KP resource.

    :param component:
    :param ara_id:
    :param kp_id:
    :return: str, resource-centric document key
    """
    return build_resource_key(component, ara_id, kp_id, target="recommendations")


def parse_unit_test_name(unit_test_key: str) -> Tuple[str, str, str, int, str, str]:
    """
    Reformat (test run key) source identifier into a well-behaved test file name.
    :param unit_test_key: original full unit test label

    :return: Tuple[ component, ara_id, kp_id, int(edge_num), test_id, edge_details_file_path]
    """
    unit_test_name = unit_test_key.split('/')[-1]

    psf = UNIT_TEST_NAME_PATTERN.match(unit_test_name)
    if psf:
        component = psf["component"]
        if component:
            component = component.upper()
            case = psf["case"]
            if case:
                tci = TEST_CASE_PATTERN.match(case)
                if tci:
                    resource_id = tci["resource_id"]
                    if resource_id:
                        rpart = resource_id.split("|")
                        if len(rpart) > 1:
                            ara_id = rpart[0]
                            kp_id = rpart[1]
                        else:
                            ara_id = None
                            kp_id = rpart[0]
                        edge_num = tci["edge_num"]
                        if edge_num:
                            test_id = tci["test_id"] if tci["test_id"] else "input"

                            return (
                                component,
                                ara_id,
                                kp_id,
                                int(edge_num),
                                test_id,
                                build_edge_details_key(component, ara_id, kp_id, edge_num)
                            )

    raise RuntimeError(f"parse_unit_test_name() '{unit_test_key}' has unknown format?")


class OneHopTestHarness:

    # Caching of processes, indexed by test_run_id (timestamp identifier as string)
    _test_run_id_2_worker_process: Dict[str, Dict] = dict()

    _test_report_database: Optional[TestReportDatabase] = None

    @classmethod
    def test_report_database(cls):
        if cls._test_report_database is None:
            cls._test_report_database = get_test_report_database()
        return cls._test_report_database

    @classmethod
    def initialize(cls):
        """
        Initialize the OneHopTestHarness environment,
        i.e. to recognized persisted test runs (in the TestReportDatabase)
        """
        logger.debug("Initializing the OneHopTestHarness environment")
        for test_run_id in cls.get_completed_test_runs():
            logger.debug(f"Found persisted test run {test_run_id} in TestReportDatabase")
            cls._test_run_id_2_worker_process[test_run_id] = {
                "command_line": None,
                "worker_process": None,
                "timeout": DEFAULT_WORKER_TIMEOUT,
                "percentage_completion": 100.0,
                "test_run_completed": True
            }

    @staticmethod
    def _generate_test_run_id() -> str:
        return datetime.now().strftime("%F_%H-%M-%S")

    def __init__(self, test_run_id: Optional[str] = None):
        """
        OneHopTestHarness constructor.

        :param test_run_id: Optional[str], known timestamp test run identifier; internally created if 'None'

        """
        self._command_line: Optional[str] = None
        self._process: Optional[WorkerProcess] = None
        self._timeout: Optional[int] = DEFAULT_WORKER_TIMEOUT
        self._percentage_completion: float = 0.0
        self._test_run_completed: bool = False
        if test_run_id is not None:
            # should be an existing test run?
            self._test_run_id = test_run_id
            self._reload_run_parameters()
        else:
            # new (or 'local') test run? no run parameters to reload?
            self._test_run_id = self._generate_test_run_id()
            self._test_run_id_2_worker_process[self._test_run_id] = {}

        # Retrieve the associated test run report object
        self._test_report: Optional[TestReport] = \
            self.test_report_database().get_test_report(identifier=self._test_run_id)

        # TODO: need a sensible path/db_key for the log file
        # self._log_file_path = self.get_absolute_file_path(document_key="test.log", create_path=True)
        self._log_file_path: Optional[str] = None

    def get_test_run_id(self) -> Optional[str]:
        return self._test_run_id

    def get_test_report(self) -> Optional[TestReport]:
        return self._test_report

    def run(
            self,
            trapi_version: Optional[str] = None,
            biolink_version: Optional[str] = None,
            triple_source: Optional[str] = None,
            ara_source: Optional[str] = None,
            one: bool = False,
            log: Optional[str] = None,
            timeout: Optional[int] = DEFAULT_WORKER_TIMEOUT
    ):
        """
        Run the SRT Testing test harness as a worker process.

        :param trapi_version: Optional[str], TRAPI version assumed for test run (default: None)

        :param biolink_version: Optional[str], Biolink Model version used in test run (default: None)

        :param triple_source: Optional[str], 'REGISTRY', directory or file from which to retrieve triples
                                             (Default: 'REGISTRY', which triggers the use of metadata, in KP entries
                                              from the Translator SmartAPI Registry, to configure the tests).

        :param ara_source: Optional[str], 'REGISTRY', directory or file from which to retrieve ARA Config.
                                             (Default: 'REGISTRY', which triggers the use of metadata, in ARA entries
                                             from the Translator SmartAPI Registry, to configure the tests).

        :param one: bool, Only use first edge from each KP file (default: False if omitted).

        :param log: Optional[str], desired Python logger level label (default: None, implying default logger)

        :param timeout: Optional[int], worker process timeout in seconds (defaults to about 120 seconds

        :return: None
        """
        # possible override of timeout here?
        self._timeout = timeout if timeout else self._timeout

        self._command_line = f"cd {ONEHOP_TEST_DIRECTORY} {CMD_DELIMITER} " + \
                             f"pytest --tb=line -vv"
        self._command_line += f" --log-cli-level={log}" if log else ""
        self._command_line += f" test_onehops.py"
        self._command_line += f" --test_run_id={self._test_run_id}"
        self._command_line += f" --TRAPI_Version={trapi_version}" if trapi_version else ""
        self._command_line += f" --Biolink_Version={biolink_version}" if biolink_version else ""
        self._command_line += f" --triple_source={triple_source}" if triple_source else ""
        self._command_line += f" --ARA_source={ara_source}" if ara_source else ""
        self._command_line += " --one" if one else ""

        logger.debug(f"OneHopTestHarness.run() command line: {self._command_line}")

        self._process = WorkerProcess(identifier=self._test_run_id, timeout=self._timeout)

        self._process.run_command(self._command_line)

        # Cache run parameters for later access as necessary
        # TODO: what about the TestReportDatabase(?)
        self._test_run_id_2_worker_process[self._test_run_id] = {
            "command_line": self._command_line,
            "worker_process": self._process,
            "timeout": self._timeout,
            "percentage_completion": 0.0,  # Percentage Completion needs to be updated later?
            "test_run_completed": False
        }

    def get_worker(self) -> Optional[WorkerProcess]:
        return self._process

    def _set_percentage_completion(self, value: float):
        if self._test_run_id in self._test_run_id_2_worker_process:
            self._test_run_id_2_worker_process[self._test_run_id]["percentage_completion"] = value
        else:
            raise RuntimeError(
                f"_set_percentage_completion(): '{str(self._test_run_id)}' Worker Process is unknown!"
            )
    
    def _get_percentage_completion(self) -> float:
        if self._test_run_id in self._test_run_id_2_worker_process:
            return self._test_run_id_2_worker_process[self._test_run_id]["percentage_completion"]
        else:
            return -1.0  # signal unknown test run process?

    def _reload_run_parameters(self):
        # TODO: do we also need to reconnect to the TestReportDatabase here?
        if self._test_run_id in self._test_run_id_2_worker_process:
            run_parameters: Dict = self._test_run_id_2_worker_process[self._test_run_id]
            self._command_line = run_parameters["command_line"]
            self._process = run_parameters["worker_process"]
            self._timeout = run_parameters["timeout"]
            self._percentage_completion = run_parameters["percentage_completion"]
            self._test_run_completed = run_parameters["test_run_completed"]
        else:
            logger.warning(
                f"Test run '{self._test_run_id}' is not associated with a Worker Process. " +
                f"May be invalid or an historic archive? Client needs to check for the latter?")
            self._command_line = None
            self._process = None
            self._timeout = DEFAULT_WORKER_TIMEOUT
            self._percentage_completion = -1.0

    def test_run_complete(self) -> bool:
        if not self._test_run_completed:
            # If there is an active WorkerProcess...
            if self._process:
                # ... then poll the Queue for task completion
                status: str = self._process.status()
                if status.startswith(WorkerProcess.COMPLETED) or \
                        status.startswith(WorkerProcess.NOT_RUNNING):
                    self._test_run_completed = True
                    if status.startswith(WorkerProcess.COMPLETED):
                        logger.debug(status)
                        self._process = None

        return self._test_run_completed

    def get_status(self) -> float:
        """
        If available, returns the percentage completion of the currently active OneHopTestHarness run.

        :return: int, 0..100 indicating the percentage completion of the test run. -1 if unknown test run ID
        """
        completed_test_runs: List[str] = self.get_completed_test_runs()
        if self._test_run_id in completed_test_runs:
            # Option 1: detection of a completed_test_run
            self._set_percentage_completion(100.0)

        elif 0.0 <= self._get_percentage_completion() < 95.0:
            for percentage_complete in self._process.get_output(timeout=1):
                logger.debug(f"Pytest % completion: {percentage_complete}")
                # We deliberately hold back declaring 100% completion to allow
                # the system to truly finish processing and return the full test report
                self._set_percentage_completion(float(percentage_complete)*0.95)

        elif self.test_run_complete():
            # Option 2, fail safe: sets completion at 100% if the task is not (or no longer) running?
            self._set_percentage_completion(100.0)

        return self._get_percentage_completion()

    def delete(self) -> str:
        try:
            if not (self.test_run_complete() and self._test_report):
                # test run still in progress...
                if self._process:

                    # this is a blocking process termination but leaves
                    # an incomplete TestReport in the TestReportDatabase
                    self._process.terminate()
                    self._process = None

                    # Remove the process from the OneHopTestHarness cache
                    if self._test_run_id in self._test_run_id_2_worker_process:
                        self._test_run_id_2_worker_process.pop(self._test_run_id)

            success = self._test_report.delete(ignore_errors=True)

        except Exception as exc:
            # Not sure what other conditions would trigger this, if any
            logger.error(f"delete() exception: '{str(exc)}'")
            success = False

        outcome: str = f"Test Run '{self._test_run_id}': "
        if success:
            self._test_report = None
            outcome += "successfully deleted!"
        else:
            outcome += "test run deletion may have been problematic. Check the server logs!"

        return outcome

    def save_json_document(self, document_type: str, document: Dict, document_key: str, is_big: bool = False):
        """
        Saves an indexed document either to a test report database or the filing system.

        :param document_type: str, category label of document type being saved (for error reporting)
        :param document: Dict, Python object to persist as a JSON document.
        :param document_key: str, indexing path for the document being saved.
        :param is_big: bool, if True, flags that the JSON file is expected to require special handling due to its size.
        """
        self.get_test_report().save_json_document(
            document_type=document_type,
            document=document,
            document_key=document_key,
            is_big=is_big
        )

    @classmethod
    def get_completed_test_runs(cls) -> List[str]:
        """
        :return: list of test run identifiers of completed test runs
        """
        return cls.test_report_database().get_available_reports()

    def get_index(self) -> Optional[Dict]:
        """
        If available, returns a test result index - KP and ARA tags - for the most recent OneHopTestHarness run.

        :return: Optional[str], JSON document KP/ARA index of unit test results. 'None' if not (yet) available.
        """
        # TODO: can some part of this operation be cached, maybe by pushing
        #       the index access down one more level, into the TestReport?
        summary: Optional[Dict] = self.get_test_report().retrieve_document(
            document_type="Summary", document_key="test_run_summary"
        )
        # Sanity check for existence of the summary...
        if not summary:
            return None

        # We extract the 'index' from the available 'test_run_summary' document
        index: Dict = dict()
        if "KP" in summary and summary["KP"]:
            index["KP"] = [str(key) for key in summary["KP"].keys()]
        if "ARA" in summary and summary["ARA"]:
            index["ARA"] = dict()
            for ara_id, ara in summary["ARA"].items():
                if "kps" in ara and ara["kps"]:
                    kps: Dict = ara["kps"]
                    index["ARA"][ara_id] = [str(key) for key in kps.keys()]

        return index

    def get_summary(self) -> Optional[Dict]:
        """
        If available, returns a test result summary for the most recent OneHopTestHarness run.

        :return: Optional[str], JSON document summary of unit test results. 'None' if not (yet) available.
        """
        summary: Optional[Dict] = self.get_test_report().retrieve_document(
            document_type="Summary", document_key="test_run_summary"
        )
        return summary

    def get_resource_summary(
            self,
            component: str,
            kp_id: str,
            ara_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Returns test result summary across all edges for given resource component.

        :param component: str, Translator component being tested: 'ARA' or 'KP'
        :param kp_id: str, identifier of a KP resource being accessed.
        :param ara_id: Optional[str], identifier of the ARA resource being accessed. May be missing or None

        :return: Optional[Dict], JSON structured document of the resource summary for a specified
                                 KP or ARA resource, or 'None' if the details are not (yet) available.
        """
        document_key: str = build_resource_summary_key(component, ara_id, kp_id)
        resource_summary: Optional[Dict] = self.get_test_report().retrieve_document(
            document_type="Resource Summary", document_key=document_key
        )
        return resource_summary

    def get_details(
            self,
            component: str,
            edge_num: str,
            kp_id: str,
            ara_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Returns test result details for given resource component and edge identities.

        :param component: str, Translator component being tested: 'ARA' or 'KP'
        :param edge_num: str, target input 'edge_num' edge number, as indexed as an edge of the JSON test run summary.
        :param kp_id: str, identifier of a KP resource being accessed.
        :param ara_id: Optional[str], identifier of the ARA resource being accessed. May be missing or None

        :return: Optional[Dict], JSON structured document of test details for a specified test edge of a
                                 KP or ARA resource, or 'None' if the details are not (yet) available.
        """
        document_key: str = build_edge_details_key(component, ara_id, kp_id, edge_num)
        details: Optional[Dict] = self.get_test_report().retrieve_document(
            document_type="Details", document_key=document_key
        )
        return details

    def get_streamed_response_file(
            self,
            component: str,
            edge_num: str,
            test_id: str,
            kp_id: str,
            ara_id: Optional[str] = None
    ) -> Generator:
        """
        Returns the TRAPI Response file path for given resource component, edge and unit test identities.

        :param component: str, Translator component being tested: 'ARA' or 'KP'
        :param edge_num: str, target input 'edge_num' edge number, as indexed as an edge of the JSON test run summary.
        :param test_id: str, target unit test identifier, one of the values noted in the
                             edge leaf nodes of the JSON test run summary (e.g. 'by_subject', etc.).
        :param kp_id: str, identifier of a KP resource being accessed.
        :param ara_id: Optional[str], identifier of the ARA resource being accessed. May be missing or None

        :return: str, TRAPI Response text data file path (generated, but not tested here for file existence)
        """
        document_key: str = build_edge_details_key(component, ara_id, kp_id, edge_num)
        return self.get_test_report().stream_document(
            document_type="Details", document_key=f"{document_key}-{test_id}"
        )

    def get_recommendations(
            self,
            component: str,
            kp_id: str,
            ara_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Returns the remedial test recommendations for a specified resource from an
        identified test run, identified by a specific set of query parameters:

        :param component: str, Translator component being tested: 'ARA' or 'KP'
        :param kp_id: str, identifier of a KP resource being accessed.
        :param ara_id: Optional[str], identifier of the ARA resource being accessed. May be missing or None

        :return: Optional[Dict], JSON structured document of test recommendations for a specified
                                 KP or ARA resource, or 'None' if the details are not (yet) available.
        """
        document_key: str = build_recommendations_key(component, ara_id, kp_id)
        resource_summary: Optional[Dict] = self.get_test_report().retrieve_document(
            document_type="Recommendations", document_key=document_key
        )
        return resource_summary
