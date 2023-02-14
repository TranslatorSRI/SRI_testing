"""
Unit tests for the backend logic of the web services application.

Note: the nature of these unit tests, even with sample data,
      means that they may take over five minutes to run each one.
      Use of a running MongoDb instance may accelerate the tests.

      TODO: February 14, 2023 - these unit tests are largely broken at the moment, but not sure if their failures
            don't just reflect the evolution of data reporting formats since the tests were initially created?
"""
from sys import stderr
from typing import Optional, Dict
from time import sleep
import logging

# Note that this test module assumes the use of the
# MOCK_TRANSLATOR_SMARTAPI_REGISTRY_METADATA and a
# FileTestDatabase, which will be initialized
# during the module import of the OneHopTestHarness below
from sri_testing.translator.sri.testing.report_db import get_test_report_database, TestReport
from tests.translator.registry import mock_registry
mock_registry(True)
get_test_report_database(True)


# This import comes after the above code... ordering is important here!
from sri_testing.translator.sri.testing.onehops_test_runner import OneHopTestHarness

logger = logging.getLogger()

CURRENT_TRAPI_VERSION: str = "1.3.0"
CURRENT_BIOLINK_VERSION: str = "3.1.1"
TEST_KP: str = "molepro"


def teardown_module(module):
    # Sanity check: We reverse the above activations after the tests(?)
    mock_registry(False)


SPACER = '\n' + '#'*120 + '\n'

MAX_TRIES = 120  # we'll try for just ~20 minutes


def _report_outcome(
        test_name: str,
        session_id: str,
        expecting_report: bool = True
):
    print(f"Processing {test_name}() from {session_id}", file=stderr)

    tries: int = 0
    percentage_completed: float = OneHopTestHarness(session_id).get_status()
    while 0.0 <= percentage_completed < 100.0:

        tries += 1
        if tries > MAX_TRIES:
            break

        logger.info(f"{percentage_completed} % completed!")
        sleep(10)  # rest 10 seconds, then try again
        percentage_completed = OneHopTestHarness(session_id).get_status()

    assert percentage_completed == 100.0, f"OneHopTestHarness status retrieval failed after {MAX_TRIES} tries?"

    summary: Optional[str] = None
    tries = 0
    while not summary:

        tries += 1
        if tries > MAX_TRIES:
            break

        summary: Optional[Dict] = OneHopTestHarness(session_id).get_summary()

        if summary:
            # got something back?!
            break

        if expecting_report:
            # nothing yet? sleep a bit?
            sleep(60)
        else:
            sleep(20)  # Should be long enough for a short timeout aborted test
            summary = OneHopTestHarness(session_id).get_summary()
            break

    if expecting_report:

        assert summary, f"{test_name}() from {session_id} is missing an expected summary?"

        logger.info(f"{test_name}() test run 'summary':\n\t{summary}\n")

        details: Optional[str] = None
        tries = 0
        while not details:

            tries += 1
            if tries > MAX_TRIES:
                break

            details = OneHopTestHarness(session_id).get_details(
                component="KP",
                edge_num="0",
                kp_id=TEST_KP
            )

            sleep(0.1)

        assert details, \
            f"{test_name}() from test run '{session_id}' is missing expected details for " + \
            f"KP tests of edge number '0' of resource {TEST_KP}?"

        logger.info(
            f"{test_name}() test run '{session_id}' details for ARA tests of " +
            f"edge number '0' of resource {TEST_KP} for test run:\n\t{details}\n"
        )

    else:
        assert not summary, \
            f"{test_name}() test run '{session_id}' has unexpected non-empty report with contents: {summary}?"


def test_run_onehop_tests_one_only():
    onehop_test = OneHopTestHarness()
    onehop_test.run(
        trapi_version=CURRENT_TRAPI_VERSION,
        biolink_version=CURRENT_BIOLINK_VERSION,
        kp_id=TEST_KP,
        one=True
    )
    _report_outcome(
        "test_run_onehop_tests_one_only",
        session_id=onehop_test.get_test_run_id()
    )


def test_run_onehop_tests_all():
    onehop_test = OneHopTestHarness()
    onehop_test.run(
        trapi_version=CURRENT_TRAPI_VERSION,
        biolink_version=CURRENT_BIOLINK_VERSION,
        kp_id=TEST_KP
    )
    _report_outcome(
        "test_run_onehop_tests_all",
        session_id=onehop_test.get_test_run_id()
    )


def test_run_onehop_tests_older_trapi_version():
    onehop_test = OneHopTestHarness()
    onehop_test.run(
        trapi_version="1.2.0",
        biolink_version=CURRENT_BIOLINK_VERSION,
        kp_id=TEST_KP,
        one=True
    )

    _report_outcome(
        "test_run_onehop_tests_older_trapi_version",
        session_id=onehop_test.get_test_run_id()
    )


def test_run_onehop_tests_older_blm_version():
    onehop_test = OneHopTestHarness()
    onehop_test.run(
        trapi_version=CURRENT_TRAPI_VERSION,
        biolink_version="1.8.2",
        kp_id=TEST_KP,
        one=True
    )
    _report_outcome(
        "test_run_onehop_tests_older_blm_version",
        session_id=onehop_test.get_test_run_id()
    )


def test_run_onehop_tests_from_registry_with_default_versioning():
    onehop_test = OneHopTestHarness()
    onehop_test.run(one=True)
    _report_outcome(
        "test_run_onehop_tests_from_registry_with_default_versioning",
        session_id=onehop_test.get_test_run_id()
    )


def test_run_onehop_tests_with_timeout():
    # 1 second timeout is much too short for this test to run
    # to completion, so a WorkerProcess timeout is triggered
    onehop_test = OneHopTestHarness()
    onehop_test.run(
        trapi_version=CURRENT_TRAPI_VERSION,
        biolink_version=CURRENT_BIOLINK_VERSION,
        one=True,
        timeout=1
    )
    _report_outcome(
        "test_run_onehop_tests_with_timeout",
        session_id=onehop_test.get_test_run_id(),
        expecting_report=False
    )


def test_test_run_deletion():
    onehop_test = OneHopTestHarness()
    test_run_id: str = onehop_test.get_test_run_id()
    test_report: TestReport = onehop_test.get_test_report()
    test_report.save_json_document(
        document_type="Fake Document",
        document={"foo": "bar"},
        document_key="fake_document",
        index=["charlatan"]
    )
    outcome: str = onehop_test.delete()
    assert onehop_test.get_test_report() is None
    assert outcome == f"Test Run '{test_run_id}': successfully deleted!"
