"""
FastAPI web service wrapper for SRI Testing harness
(i.e. for reports to a Translator Runtime Status Dashboard)
"""
from typing import Optional, Dict, List, Generator, Union, Tuple
from os.path import dirname, abspath

from pydantic import BaseModel

import uvicorn

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from reasoner_validator.report import CodeDictionary

from tests.translator.trapi import PATCHED_140_SCHEMA_FILEPATH

from reasoner_validator.versioning import (
    get_latest_version,
    SemVer,
    SemVerError,
    SemVerUnderspecified
)

from tests.onehop.util import get_unit_test_definitions
from sri_testing.translator.sri.testing.onehops_test_runner import (
    OneHopTestHarness,
    DEFAULT_WORKER_TIMEOUT
)

import logging

# SYSLOG_LEVEL: str = getenv("LOGGING_LEVEL", default="WARNING")
# logging.basicConfig(stream=stderr, level=SYSLOG_LEVEL)
logger = logging.getLogger(__name__)

# syslog_level_msg = f"Application logging level set to '{SYSLOG_LEVEL}'"
# logger.info(syslog_level_msg)
# print(syslog_level_msg, file=stderr)

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:80",
    "http://localhost:8080"
    "http://localhost:8090",
    "http://dashboard",
    "http://dashboard:80",
    "http://dashboard:8080"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    # TODO: need to perhaps do some initialization here of the
    #       OneHopTesting class level cache of test_runs?
    OneHopTestHarness.initialize()


favicon_path = f"{abspath(dirname(__file__))}/img/favicon.ico"


@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse(favicon_path)


class ResourceRegistry(BaseModel):
    message: str = ""
    KPs: Dict[str, Dict[str, List[str]]]
    ARAs: Dict[str, Dict[str, List[str]]]


# Treat the registry catalog as an initialized singleton, to enhance application performance
the_resources: Tuple[Dict[str, Dict[str, List[str]]], Dict[str, Dict[str, List[str]]]] = \
        OneHopTestHarness.testable_resources_catalog_from_registry()


@app.get(
    "/registry",
    tags=['report'],
    response_model=Union[ResourceRegistry, str],
    summary="Retrieve the list of testable resources (KPs and ARAs) published in the Translator SmartAPI Registry."
)
async def get_resources_from_registry(refresh: bool = False) -> Union[ResourceRegistry, str]:
    """
    Returns a list of ARA and KP available for testing from the Translator SmartAPI Registry.
    Note that only Translator resources with their **info.x-trapi.test_data_location** properties set are reported.

    - 2-Tuple(Dict[ara_id*, List[str], Dict[kp_id*, List[str]) inventory of available KPs and ARAs, keyed with the
      reference ('object') id's of InfoRes CURIES and where values are lists of testable x-maturity environments
    \f
    :return: ResourceRegistry, inventory of available KPs and ARAs with the testable x-maturity environment types.
    """
    global the_resources
    if refresh:
        the_resources = OneHopTestHarness.testable_resources_catalog_from_registry()

    message: str
    if the_resources is not None:
        message = "Translator resources found!"
        return ResourceRegistry(message=message, KPs=the_resources[0], ARAs=the_resources[1])
    else:
        message = "Translator SmartAPI Registry currently offline?"
        return message


###########################################################
# We don't instantiate the full TRAPI models here but
# just use an open-ended dictionary which should have
# query_graph, knowledge_graph and results JSON tag-values
###########################################################
class TestRunParameters(BaseModel):
    # TODO: we ignore the other SRI Testing parameters
    #       for the initial design of the web service
    #
    # # Which Test to Run?
    # teststyle: Optional[str] = "all"
    #
    # # Only use first edge from each KP file
    # one: bool = False
    #
    # (Optional) reference (object) identifier of the ARA InfoRes CURIE
    # designating an ARA which is the target of validation in the new test run.
    ara_id: Optional[str] = None

    # (Optional) reference (object) identifier of the ARA InfoRes CURIE
    # designating a KP which is the target of validation in the new test run.
    kp_id: Optional[str] = None

    # (Optional) x_maturity environment target for test run. We assume here that any and both ARA and KP
    # specified above have servers block endpoints specified under the corresponding 'x-maturity' tag in
    # their respective Translator SmartAPI Registry entry 'servers' block.
    # If unspecified, then SRI Testing makes an educated guess of which 'x-maturity' endpoint to test.
    x_maturity: Optional[str] = None

    # (Optional) TRAPI version override against which
    # SRI Testing will be applied to Translator KPs and ARA's.
    # This version will override Translator SmartAPI Registry
    # KP or ARA entry specified 'x-trapi' metadata tag value
    # specified TRAPI version (Default: None).
    trapi_version: Optional[str] = None

    # (Optional) Biolink Model version override against which
    # SRI Testing will be applied to Translator KPs and ARA's.
    # This version will override Translator SmartAPI Registry
    # KP entry specified 'x-translator' metadata tag value
    # specified Biolink Model version (Default: None)..
    biolink_version: Optional[str] = None

    # (Optional) number of test edges to process from
    # each KP test edge data input file (Note: system default is 100)
    max_number_of_edges: Optional[int] = None

    # Worker Process data access timeout; defaults to DEFAULT_WORKER_TIMEOUT
    # which implies caller blocking until the data is available
    timeout: Optional[int] = DEFAULT_WORKER_TIMEOUT

    # Python logging framework spec, e.g. DEBUG, INFO, etc.
    log: Optional[str] = None


class TestRunSession(BaseModel):

    test_run_id: str
    errors: Optional[List[str]] = None


def _is_valid_version_spec(version_string: str):
    try:
        SemVer.from_string(version_string)
    except SemVerUnderspecified:
        # it's ok that it's underspecified?
        pass
    except SemVerError:
        return False

    return True


@app.post(
    "/run_tests",
    tags=['run'],
    response_model=TestRunSession,
    summary="Initiate an SRI Testing Run"
)
async def run_tests(test_parameters: Optional[TestRunParameters] = None) -> TestRunSession:
    """
    Initiate an SRI Testing Run with TestRunParameters:

    - **ara_id**: Optional[str], identifier of the ARA resource whose indirect KP test results are being accessed
    - **kp_id**: Optional[str], identifier(s) of the KP resource(s) whose test results are specifically being accessed.
        Note that 'kp_id' may be a comma delimited list of strings, in which case, any or all of the indicated KP
        identifiers are included in the test run, with or without an ARA identifier, interpreted as follows:

    *Case 1* - non-empty kp_id, empty ara_id: just return  summary of specified KP resource(s) for all ARAs calling KPs.
    *Case 2* - non-empty kp_id, ara_id == 'SKIP': only just test the specified KP resource(s) (without calling ARAs).
    *Case 3* - non-empty ara_id, non-empty kp_id: return the one specific KP(s) tested via the specified ARA
    *Case 4* - non-empty ara_id, empty kp_id: validate against all the KPs specified by the ARA configuration file
    *Case 5* - empty ara_id and kp_id: validate all Registry KPs and ARAs (long-running validation! Be careful now!)

    The **'ara_id'** and **'kp_id'** may be a scalar string, or a comma-delimited set of strings.
    If the 'source' string includes a single asterix ('\\*'), it is treated as a wildcard match to the
    infores identifier being filtered. Note that all identifiers here should be the reference (object)
    identifiers of the Infores CURIE of the target resource(s).

    - **x_maturity**: Optional[str], **x_maturity** environment target for test run (system chooses if not specified)
    - **trapi_version**: Optional[str], possible TRAPI version overriding Translator SmartAPI 'Registry' specification.
    - **biolink_version**: Optional[str], possible Biolink Model version overriding Registry specification.
    - **max_number_of_edges**: Optional[int], number of test edges to process from  each KP test edge data input file
                                             (Note: system default is 100)
    - **timeout**: Optional[int], query timeout
    - **log**: Optional[str], Python log setting (i.e. "DEBUG", "INFO", etc)
    \f
    :param test_parameters: TestRunParameters
    :return: TestRunSession (just 'test_run_id' for now)
    """

    ara_id: Optional[str] = None
    kp_id: Optional[str] = None
    x_maturity: Optional[str] = None
    trapi_version: Optional[str] = None
    biolink_version: Optional[str] = None
    max_number_of_edges: Optional[int] = None
    log: Optional[str] = None
    timeout: int = DEFAULT_WORKER_TIMEOUT

    errors: List[str] = list()
    if test_parameters:

        if test_parameters.ara_id:
            ara_id = test_parameters.ara_id

        if test_parameters.kp_id:
            kp_id = test_parameters.kp_id

        if test_parameters.x_maturity:
            x_maturity = test_parameters.x_maturity

        if test_parameters.trapi_version:
            trapi_version = test_parameters.trapi_version
            if not _is_valid_version_spec(trapi_version):
                errors.append(f"'trapi_version' parameter '{trapi_version}' is not a valid SemVer string!")
            else:
                trapi_version = get_latest_version(test_parameters.trapi_version)

        if test_parameters.biolink_version:
            biolink_version = test_parameters.biolink_version
            if not _is_valid_version_spec(biolink_version):
                errors.append(f"'biolink_version' parameter '{biolink_version}' is not a valid SemVer string!")

        if test_parameters.max_number_of_edges:
            max_number_of_edges = test_parameters.max_number_of_edges

        timeout = test_parameters.timeout if test_parameters.timeout else DEFAULT_WORKER_TIMEOUT

        if test_parameters.log:
            log = test_parameters.log.upper()
            if log not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                errors.append(f"'log' parameter '{log}' is not a valid Python logging specification!")

    if errors:
        return TestRunSession(test_run_id="Invalid Parameters - test run not started...", errors=errors)

    # Constructor initializes a fresh
    # test run with a new identifier
    test_harness = OneHopTestHarness()

    test_harness.run(
        ara_id=ara_id,
        kp_id=kp_id,
        x_maturity=x_maturity,
        trapi_version=trapi_version,
        biolink_version=biolink_version,
        max_number_of_edges=max_number_of_edges,
        log=log,
        timeout=timeout
    )

    return TestRunSession(test_run_id=test_harness.get_test_run_id())


class TestRunStatus(BaseModel):
    test_run_id: str
    percent_complete: float


@app.get(
    "/status",
    tags=['report'],
    response_model=TestRunStatus,
    summary="Retrieve the percentage completion status of a specified SRI Testing run."
)
async def get_status(test_run_id: str) -> TestRunStatus:
    """
    Returns the percentage completion status of the current OneHopTestHarness test run.

    \f
    :param test_run_id: test_run_id: test run identifier (as returned by /run_tests endpoint).

    :return: TestRunStatus, with fields 'test_run_id' and 'percent_complete', the latter being
                             an integer 0..100 indicating the percentage completion of the test run.
    """

    percent_complete: float = OneHopTestHarness(test_run_id=test_run_id).get_status()

    return TestRunStatus(test_run_id=test_run_id, percent_complete=round(percent_complete, 4))


class TestRunDeletion(BaseModel):
    test_run_id: str
    outcome: str


@app.delete(
    "/delete",
    tags=['report'],
    response_model=TestRunDeletion,
    summary="Cancel/delete a currently running SRI Testing run or delete a completed test run."
)
async def delete(test_run_id: str) -> TestRunDeletion:
    """
    Deletes a OneHopTestHarness test run. The test run may still be in process, or may be a completed test_run.
    In the former case, the test_run is simply cancelled, with results discarded. In the latter case,
    the test_run is deleted from the TestRunDatabase.

    \f
    :param test_run_id: test_run_id: test run identifier (as returned by /run_tests endpoint).

    :return: TestRunDeletion, with fields 'test_run_id' and 'status', the latter
             being a simple text message confirming the outcome of the operation.
    """
    outcome: str = OneHopTestHarness(test_run_id=test_run_id).delete()
    return TestRunDeletion(test_run_id=test_run_id, outcome=outcome)


class TestRunList(BaseModel):
    test_runs: List[str]


@app.get(
    "/test_runs",
    tags=['report'],
    response_model=TestRunList,
    summary="Retrieve the list of completed test runs."
)
async def get_test_run_list(
        ara_id: Optional[str] = None,
        kp_id: Optional[str] = None,
        latest: bool = False
) -> TestRunList:
    """
    Returns the catalog of completed OneHopTestHarness test runs, possibly filtered by ara_id and/or kp_id.

    - **ara_id**: identifier of the ARA resource whose indirect KP test results are being accessed
    - **kp_id**: identifier of the KP resource whose test results are specifically being accessed.
        - Case 1 - non-empty kp_id, empty ara_id == return test runs of the one directly tested KP resource
        - Case 2 - non-empty ara_id, non-empty kp_id == return test run of one specific KP tested via the ARA
        - Case 3 - non-empty ara_id, empty kp_id == return test runs of all KPs being tested under the ARA
        - Case 4 - empty ara_id and kp_id == identifiers for all available test runs returned.

    **Note:** that the 'kp_id' or 'ara_id' may be a single infores reference identifier or a comma-delimited list of
    such identifiers, for exact matching or wildcard matching by inclusion of a one sided or double sided single asterix
    ('*') wild card pattern; i.e. single sided 'automat-*' will match both 'automat-gtex' and 'automat-robokop'
    i.e. double sided 'automat-*kop' will match both 'automat-covidkop' and 'automat-robokop' but not 'automat-gtex').

    - **latest**: bool, optional flag constrains run list to just report 'latest' test run (default: False).

    \f
    :param ara_id: identifier of the ARA resource whose indirect KP test results are being accessed
    :param kp_id: identifier of the KP resource whose test results are specifically being accessed.
        - Case 1 - non-empty kp_id, empty ara_id == return test runs of the one directly tested KP resource
        - Case 2 - non-empty ara_id, non-empty kp_id == return test run of one specific KP tested via the ARA
        - Case 3 - non-empty ara_id, empty kp_id == return test runs of all KPs being tested under the ARA
        - Case 4 - empty ara_id and kp_id == identifiers for all available test runs returned.
    :param latest: bool, optional boolean flag constrains run_list to 'latest' test run (default: False).
    :return: TestRunList, sorted list of timestamp identifiers of completed OneHopTestHarness test runs.
    """
    test_runs: List[str] = OneHopTestHarness.get_completed_test_runs(ara_id=ara_id, kp_id=kp_id)
    # Sort the test_run identifiers, which are timestamps with lexical ordering?
    test_runs.sort(reverse=True)
    if test_runs and latest:
        # test_run_id's are timestamps sorted lexically
        test_runs = test_runs[0:1]
    return TestRunList(test_runs=test_runs)


class Message(BaseModel):
    message: str


class TestRunSummary(BaseModel):
    test_run_id: str
    summary: Dict


@app.get(
    "/index",
    tags=['report'],
    response_model=TestRunSummary,
    summary="Retrieve the index - KP and ARA resource tags - within a completed specified OneHopTestHarness test run.",
    responses={404: {"model": Message}}
)
async def get_index(test_run_id: str) -> Union[TestRunSummary, JSONResponse]:
    """
    Returns a JSON index of all of the KP and ARA resource tags in a completed OneHopTestHarness test run.

    \f
    :param test_run_id: test_run_id: test run identifier (as returned by /run_tests endpoint).

    :return: TestRunSummary, with fields 'test_run_id' and 'summary', the latter being a
                             JSON document summary of available unit test results.
    :raises: HTTPException(404) if the summary is not (yet?) available.
    """

    index: Optional[Dict] = OneHopTestHarness(test_run_id=test_run_id).get_index()

    if index is not None:
        return TestRunSummary(test_run_id=test_run_id, summary=index)
    else:
        return JSONResponse(
            status_code=404,
            content={
                "message": f"Index for test run '{test_run_id}' is not (yet) available?"
            }
        )


@app.get(
    "/summary",
    tags=['report'],
    response_model=TestRunSummary,
    summary="Retrieve the summary of a completed specified OneHopTestHarness test run.",
    responses={404: {"model": Message}}
)
async def get_summary(test_run_id: str) -> Union[TestRunSummary, JSONResponse]:
    """
    Returns a JSON summary report of results for a completed OneHopTestHarness test run.

    \f
    :param test_run_id: test_run_id: test run identifier (as returned by /run_tests endpoint).

    :return: TestRunSummary, with fields 'test_run_id' and 'summary', the latter being a
                             JSON document summary of available unit test results.
    :raises: HTTPException(404) if the summary is not (yet?) available.
    """

    summary: Optional[Dict] = OneHopTestHarness(test_run_id=test_run_id).get_summary()

    if summary is not None:
        return TestRunSummary(test_run_id=test_run_id, summary=summary)
    else:
        return JSONResponse(
            status_code=404,
            content={
                "message": f"Summary for test run '{test_run_id}' is not (yet) available?"
            }
        )


@app.get(
    "/resource",
    tags=['report'],
    response_model=TestRunSummary,
    summary="Retrieve the test result summary for a specified resource from a specified SRI Testing Run.",
    responses={400: {"model": Message}, 404: {"model": Message}}
)
async def get_resource_summary(
        test_run_id: str,
        ara_id: Optional[str] = None,
        kp_id: Optional[str] = None
) -> Union[TestRunSummary, JSONResponse]:
    """
    Return result summary for a specific KP resource in an
    identified test run, identified by a specific set of query parameters:
    - **test_run_id**: test run being accessed.
    - **ara_id**: identifier of the ARA resource whose indirect KP test results are being accessed
    - **kp_id**: identifier of the KP resource whose test results are specifically being accessed.
        - Case 1 - non-empty kp_id, empty ara_id == just return the summary of the one directly tested KP resource
        - Case 2 - non-empty ara_id, non-empty kp_id == return the one specific KP tested via the specified ARA
        - Case 3 - non-empty ara_id, empty kp_id == return all the KPs being tested under the specified ARA
        - Case 4 - empty ara_id and kp_id == error ...at least one of 'ara_id' and 'kp_id' needs to be provided.

    \f
    :param test_run_id: test run identifier (as returned by /run_tests endpoint).
    :param ara_id: identifier of the ARA resource whose indirect KP test results are being accessed
    :param kp_id: identifier of the KP resource whose test results are specifically being accessed.
        - Case 1 - non-empty kp_id, empty ara_id == just return the summary of the one directly tested KP resource
        - Case 2 - non-empty ara_id, non-empty kp_id == return the one specific KP tested via the specified ARA
        - Case 3 - non-empty ara_id, empty kp_id == return all the KPs being tested under the specified ARA
        - Case 4 - empty ara_id and kp_id == error ...at least one of 'ara_id' and 'kp_id' needs to be provided.

    :return: TestRunSummary, echoing input parameters alongside the requested 'summary', the latter
                             which is a resource summary JSON document for the specified unit test.

    :raises: HTTPException(404) if the requested edge unit test details are not (yet?) available.
    """
    # TODO: maybe we should validate the test_run_id, ara_id and kp_id against the /index catalog?
    test_run = OneHopTestHarness(test_run_id=test_run_id)
    summary: Optional[Dict]
    if ara_id:
        if kp_id:
            # Case 2: return the one specific KP tested via the specified ARA
            summary = test_run.get_resource_summary(component="ARA", ara_id=ara_id, kp_id=kp_id)
        else:
            # Case 3: return all the KPs being tested under the specified ARA
            # TODO: Merged ARA implementation without a specific kp_id, needs a bit more thought.
            return JSONResponse(status_code=400, content={"message": "Null kp_id parameter is not yet supported?"})
    else:  # empty 'ara_id'
        if kp_id:
            # Case 1: just return the summary of the one directly tested KP resource
            summary: Optional[Dict] = test_run.get_resource_summary(component="KP", kp_id=kp_id)
        else:
            # Case 4: error...at least one of 'ara_id' and 'kp_id' needs to be provided.
            return JSONResponse(
                status_code=400,
                content={"message": "The 'ara_id' and 'kp_id' cannot both be empty parameters!"}
            )
    if summary is not None:
        return TestRunSummary(test_run_id=test_run_id, summary=summary)
    else:
        return JSONResponse(
            status_code=404,
            content={
                "message": f"Resource summary, for ara_id '{str(ara_id)}' and kp_id '{str(kp_id)}', " +
                           f"is not (yet) available from test run '{test_run_id}'?"
            }
        )


class TestRunEdgeDetails(BaseModel):
    details: Dict


@app.get(
    "/details",
    tags=['report'],
    response_model=TestRunEdgeDetails,
    summary="Retrieve the test result details for a specified SRI Testing Run input edge.",
    responses={400: {"model": Message}, 404: {"model": Message}}
)
async def get_details(
    test_run_id: str,
    edge_num: str,
    ara_id: Optional[str] = None,
    kp_id: Optional[str] = None
) -> Union[TestRunEdgeDetails, JSONResponse]:
    """
    Retrieve the test result details for a specified ARA or KP resource
    in a given test run defined by the following query path parameters:
    - **test_run_id**: test run being accessed.
    - **edge_num**: target input 'edge_num' edge number, as found in edge leaf nodes of the JSON test run summary.

    - **ara_id**: identifier of the ARA resource whose indirect KP test results are being accessed
    - **kp_id**: identifier of the KP resource whose test results are specifically being accessed.
        - Case 1 - non-empty kp_id, empty ara_id == just return the summary of the one directly tested KP resource
        - Case 2 - non-empty ara_id, non-empty kp_id == return the one specific KP tested via the specified ARA
        - Case 3 - non-empty ara_id, empty kp_id == return all the KPs being tested under the specified ARA
        - Case 4 - empty ara_id and kp_id == error ...at least one of 'ara_id' and 'kp_id' needs to be provided.

    \f
    :param test_run_id: test run identifier (as returned by /run_tests endpoint).
    :param edge_num: target input 'edge_num' edge number, as found in edge leaf nodes of the JSON test run summary.

    :param ara_id: identifier of the ARA resource whose indirect KP test results are being accessed
    :param kp_id: identifier of the KP resource whose test results are specifically being accessed.
        - Case 1 - non-empty kp_id, empty ara_id == just return the summary of the one directly tested KP resource
        - Case 2 - non-empty ara_id, non-empty kp_id == return the one specific KP tested via the specified ARA
        - Case 3 - non-empty ara_id, empty kp_id == return all the KPs being tested under the specified ARA
        - Case 4 - empty ara_id and kp_id == error ...at least one of 'ara_id' and 'kp_id' needs to be provided.

    :return: TestRunEdgeDetails, echoing input parameters alongside the requested 'details', the latter which is a
                                 details JSON document for the specified unit test.
             or HTTP Status Code(400) unsupported parameter configuration.
             or HTTP Status Code(404) if the requested TRAPI response JSON text data file is not (yet?) available.
    """
    # TODO: maybe we should validate the test_run_id, ara_id and kp_id against the /index catalog?
    test_run = OneHopTestHarness(test_run_id=test_run_id)
    details: Optional[Dict]
    if ara_id:
        if kp_id:
            # Case 2: return the one specific KP tested via the specified ARA
            details = test_run.get_details(component="ARA", ara_id=ara_id, kp_id=kp_id, edge_num=edge_num)
        else:
            # Case 3: return all the KPs being tested under the specified ARA
            # TODO: Merged ARA implementation without a specific kp_id, needs a bit more thought.
            return JSONResponse(status_code=400, content={"message": "Null kp_id parameter is not yet supported?"})
    else:  # empty 'ara_id'
        if kp_id:
            # Case 1: just return the summary of the one directly tested KP resource
            details: Optional[Dict] = test_run.get_details(component="KP", kp_id=kp_id, edge_num=edge_num)
        else:
            # Case 4: error...at least one of 'ara_id' and 'kp_id' needs to be provided.
            return JSONResponse(status_code=400, content={"message": "At least a 'kp_id' must be specified!"})

    if details is not None:
        return TestRunEdgeDetails(details=details)
    else:
        return JSONResponse(
            status_code=404,
            content={
                "message": f"Edge details, for ara_id '{str(ara_id)}' and kp_id '{str(kp_id)}', " +
                           f"are not (yet) available from test run '{test_run_id}'?"
            }
        )


@app.get(
    "/response",
    tags=['report'],
    summary="Directly stream the TRAPI response JSON message for a " +
            "specified SRI Testing unit test of a given input edge.",
    responses={400: {"model": Message}, 404: {"model": Message}}
)
async def get_response(
        test_run_id: str,
        edge_num: str,
        test_id: str,
        ara_id: Optional[str] = None,
        kp_id: Optional[str] = None
) -> Union[StreamingResponse, JSONResponse]:
    """
    Return full TRAPI response message as a streamed downloadable text file, if available, for a specified unit test
    of an edge, as identified test run defined by the following query path parameters:

    - **test_run_id**: test run being accessed.
    - **edge_num**: target input 'edge_num' edge number, as found in edge leaf nodes of the JSON test run summary.
    - **test_id**: target unit test identifier, one of the values noted in the edge leaf nodes of the test run summary.

    - **ara_id**: identifier of the ARA resource whose indirect KP test results are being accessed
    - **kp_id**: identifier of the KP resource whose test results are specifically being accessed.
        - Case 1 - non-empty kp_id, empty ara_id == just return the summary of the one directly tested KP resource
        - Case 2 - non-empty ara_id, non-empty kp_id == return the one specific KP tested via the specified ARA
        - Case 3 - non-empty ara_id, empty kp_id == error... option not provided here ... too much bandwidth!
        - Case 4 - empty ara_id and kp_id == error ...At least a 'kp_id' must be specified!

    \f
    :param test_run_id: str, test run identifier (as returned by /run_tests endpoint)
    :param edge_num: str, target input 'edge_num' edge number, as found in edge leaf nodes of the JSON test run summary.
    :param test_id: str, target unit test identifier, one of the values noted in the
                         edge leaf nodes of the JSON test run summary (e.g. 'by_subject', etc.).

    :param ara_id: identifier of the ARA resource whose indirect KP test results are being accessed
    :param kp_id: identifier of the KP resource whose test results are specifically being accessed.
        - Case 1 - non-empty kp_id, empty ara_id == just return the summary of the one directly tested KP resource
        - Case 2 - non-empty ara_id, non-empty kp_id == return the one specific KP tested via the specified ARA
        - Case 3 - non-empty ara_id, empty kp_id == error... option not provided here ... too much bandwidth!
        - Case 4 - empty ara_id and kp_id == error ...At least a 'kp_id' must be specified!

    :return: StreamingResponse, HTTP status code 200 with downloadable text file of TRAPI response
             or HTTP Status Code(400) unsupported parameter configuration.
             or HTTP Status Code(404) if the requested TRAPI response JSON text data file is not (yet?) available.
    """
    # TODO: maybe we should validate the test_run_id, ara_id and kp_id against the /index catalog?
    test_run = OneHopTestHarness(test_run_id=test_run_id)
    try:
        content_generator: Generator
        if ara_id:
            if kp_id:
                # Case 2: return the one specific KP tested via the specified ARA
                content_generator = test_run.get_streamed_response_file(
                    component="ARA",
                    ara_id=ara_id,
                    kp_id=kp_id,
                    edge_num=edge_num,
                    test_id=test_id
                )
            else:
                # Case 3: error... option not provided here ... too much bandwidth!
                return JSONResponse(
                    status_code=400,
                    content={"message": "Null 'kp_id' is not supported with a non-null 'ara_id'!"}
                )
        else:  # empty 'ara_id'
            if kp_id:
                # Case 1: just return the summary of the one directly tested KP resource
                content_generator = test_run.get_streamed_response_file(
                    component="KP",
                    kp_id=kp_id,
                    edge_num=edge_num,
                    test_id=test_id
                )
            else:
                # Case 4: error...at least 'kp_id' needs to be provided.
                return JSONResponse(status_code=400, content={"message": "At least a 'kp_id' must be specified!"})

        return StreamingResponse(
            content=content_generator,
            media_type="application/json"
        )
    except RuntimeError:
        return JSONResponse(
            status_code=404,
            content={
                "message": f"TRAPI Response JSON text file for unit test {test_id} for edge {edge_num} " +
                           f"for ara_id '{str(ara_id)}' and kp_id '{str(kp_id)}', " +
                           f"from test run '{test_run_id}', is not (yet) available?"
            }
        )


class TestRecommendations(BaseModel):
    test_run_id: str
    recommendations: Dict


@app.get(
    "/recommendations",
    tags=['report'],
    response_model=TestRecommendations,
    summary="Retrieve the test run remedial recommendations for a specified resource from a specified SRI Testing Run.",
    responses={400: {"model": Message}, 404: {"model": Message}}
)
async def get_recommendations(
        test_run_id: str,
        ara_id: Optional[str] = None,
        kp_id: Optional[str] = None
) -> Union[TestRecommendations, JSONResponse]:
    """
    Return the remedial recommendations for a specified resource from an
    identified test run, identified by a specific set of query parameters:
    - **test_run_id**: test run being accessed.
    - **ara_id**: identifier of the ARA resource whose indirect KP test results are being accessed
    - **kp_id**: identifier of the KP resource whose test results are specifically being accessed.
        - Case 1 - non-empty kp_id, empty ara_id == just return the summary of the one directly tested KP resource
        - Case 2 - non-empty ara_id, non-empty kp_id == return the one specific KP tested via the specified ARA
        - Case 3 - non-empty ara_id, empty kp_id == return all the KPs being tested under the specified ARA
        - Case 4 - empty ara_id and kp_id == error ...at least one of 'ara_id' and 'kp_id' needs to be provided.

    \f
    :param test_run_id: test run identifier (as returned by /run_tests endpoint).
    :param ara_id: identifier of the ARA resource whose indirect KP test results are being accessed
    :param kp_id: identifier of the KP resource whose test results are specifically being accessed.
        - Case 1 - non-empty kp_id, empty ara_id == just return the summary of the one directly tested KP resource
        - Case 2 - non-empty ara_id, non-empty kp_id == return the one specific KP tested via the specified ARA
        - Case 3 - non-empty ara_id, empty kp_id == return all the KPs being tested under the specified ARA
        - Case 4 - empty ara_id and kp_id == error ...at least one of 'ara_id' and 'kp_id' needs to be provided.

    :return: TestRunSummary, echoing input parameters alongside the requested 'summary', the latter
                             which is a recommendations JSON document for the specified unit test.

    :raises: HTTPException(404) if the requested edge unit test details are not (yet?) available.
    """
    # TODO: maybe we should validate the test_run_id, ara_id and kp_id against the /index catalog?
    test_run = OneHopTestHarness(test_run_id=test_run_id)
    recommendations: Optional[Dict]
    if ara_id:
        if kp_id:
            # Case 2: return the one specific KP tested via the specified ARA
            recommendations = test_run.get_recommendations(component="ARA", ara_id=ara_id, kp_id=kp_id)
        else:
            # Case 3: return recommendations for all the KPs being tested under the specified ARA
            # TODO: Merged ARA implementation without a specific kp_id, needs a bit more thought.
            return JSONResponse(status_code=400, content={"message": "Null kp_id parameter is not yet supported?"})
    else:  # empty 'ara_id'
        if kp_id:
            # Case 1: just return the recommendations of the one directly tested KP resource
            recommendations: Optional[Dict] = test_run.get_recommendations(component="KP", kp_id=kp_id)
        else:
            # Case 4: error...at least one of 'ara_id' and 'kp_id' needs to be provided.
            return JSONResponse(
                status_code=400,
                content={"message": "The 'ara_id' and 'kp_id' cannot both be empty parameters!"}
            )
    if recommendations is not None:
        return TestRecommendations(test_run_id=test_run_id, recommendations=recommendations)
    else:
        return JSONResponse(
            status_code=404,
            content={
                "message": f"Resource summary, for ara_id '{str(ara_id)}' and kp_id '{str(kp_id)}', " +
                           f"is not (yet) available from test run '{test_run_id}'?"
            }
        )


class ValidationCodes(BaseModel):
    code: str
    entry: Dict


@app.get(
    "/code_entry",
    tags=['report'],
    response_model=ValidationCodes,
    summary="Retrieve the validation code subtree - message template, description or 'all' - for a given code.",
    responses={400: {"model": Message}, 404: {"model": Message}}
)
async def get_code_entry(
        code: str,
        facet: Optional[str] = None,
        distinct: bool = False
) -> Union[ValidationCodes, JSONResponse]:
    """
    Retrieves validation distinct validation message code or a subtree (for partial code paths).
    Either the message template and/or description 'facet' of the code may be returned.

    :param code: str, 'dot' path specified code identifier from reasoner-validator codes.yaml validation message codes.
    :param facet: Optional[str], constraint on code entry facet to be returned; if specified,
                  should be either "message" or "description" (default: return both facets of the code entry)
    :param distinct: Optional[bool], only return entry if it is distinct code entry (default: False)
    :return: ValidationCodes, entry for code, may be subtree with all leaves, or single entry leaf, with specified
                              entry facets raises JSONResponse, if code is unknown (or service unavailable).
    """
    if facet:
        facet = facet.lower()
        if facet not in ["message", "description"]:
            return JSONResponse(
                status_code=400,
                content={
                    "message": f"Unknown information type '{facet}' requested?"
                }
            )
        facet_label = f" '{facet}' "
    else:
        facet_label = ''

    result = CodeDictionary.get_code_subtree(code=code, facet=facet, is_leaf=distinct)

    if result is not None:
        return ValidationCodes(code=code, entry=result[1])
    else:
        if distinct:
            as_item = "distinct code"
        else:
            as_item = "as subtree"
        return JSONResponse(
            status_code=404,
            content={
                "message": f"Validation message code{facet_label if facet_label else ' '}" +
                           f"information unavailable for '{code}' as {as_item}?"
            }
        )


@app.get(
    "/unit_tests",
    tags=['report'],
    # response_model=Dict,
    summary="Retrieves a simple dictionary of SRI Testing unit test descriptions.",
    responses={400: {"model": Message}, 404: {"model": Message}}
)
async def get_unit_test_descriptions() -> Union[Dict, JSONResponse]:
    """
    Retrieves a simple dictionary of SRI Testing unit test descriptions.
    This first iteration is a simple GET call to a default dictionary of OneHop unit test descriptions.

    :return: Optional[Dict], catalog of unit test descriptions indexed by test name string (in snake case)
    """

    result = get_unit_test_definitions()

    if result is not None:
        return result
    else:
        return JSONResponse(
            status_code=404,
            content={
                "message": f"Unit test catalog unavailable?"
            }
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090)
