"""
Unit tests for the backend logic of the web services application.

Note: the nature of these unit tests, even with sample data,
      means that they may take over five minutes to run each one.
      Use of a running MongoDb instance may accelerate the tests.
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


def teardown_module(module):
    # Sanity check: We reverse the above activations after the tests(?)
    mock_registry(False)


SPACER = '\n' + '#'*120 + '\n'

MAX_TRIES = 5  # we'll try for just 20 minutes


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

        print(f"{percentage_completed }% completed!", file=stderr)
        sleep(60)  # rest a minute then try again
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

        print(f"{test_name}() test run 'summary':\n\t{summary}\n", file=stderr)

        details: Optional[str] = None
        tries = 0
        while not details:

            tries += 1
            if tries > MAX_TRIES:
                break

            details = OneHopTestHarness(session_id).get_details(
                component="ARA",
                edge_num="1",
                ara_id="arax",
                kp_id="sri-reference-kg"
            )

            sleep(0.1)

        assert details, \
            f"{test_name}() from test run '{session_id}' is missing expected details for " + \
            f"ARA tests of edge number '1' of resource 'sri-reference-kg'?"

        print(
            f"{test_name}() test run '{session_id}' details for ARA tests of " +
            f"edge number '1' of resource 'arax' for test run:\n\t{details}\n",
            file=stderr
        )

    else:
        assert not summary, \
            f"{test_name}() test run '{session_id}' has unexpected non-empty report with contents: {summary}?"


def test_run_local_onehop_tests_one_only():
    onehop_test = OneHopTestHarness()
    onehop_test.run(
        trapi_version="1.3",
        biolink_version="2.4.8",
        kp_id="sri-reference-kg",
        ara_id="arax",
        one=True
    )
    _report_outcome(
        "test_run_local_onehop_tests",
        session_id=onehop_test.get_test_run_id()
    )


def test_run_local_onehop_tests_all():
    onehop_test = OneHopTestHarness()
    onehop_test.run(
        trapi_version="1.3",
        biolink_version="2.4.8",
        kp_id="sri-reference-kg",
        ara_id="arax"
    )
    _report_outcome(
        "test_run_local_onehop_tests",
        session_id=onehop_test.get_test_run_id()
    )


def test_run_local_onehop_tests_all_older_trapi_version():
    onehop_test = OneHopTestHarness()
    onehop_test.run(
        trapi_version="1.0.0",
        biolink_version="2.4.8",
        kp_id="sri-reference-kg",
        ara_id="arax"
    )

    _report_outcome(
        "test_run_local_onehop_tests",
        session_id=onehop_test.get_test_run_id()
    )


def test_run_local_onehop_tests_all_older_blm_version():
    onehop_test = OneHopTestHarness()
    onehop_test.run(
        trapi_version="1.2.0",
        biolink_version="1.8.2",
        kp_id="sri-reference-kg",
        ara_id="arax"
    )
    _report_outcome(
        "test_run_local_onehop_tests",
        session_id=onehop_test.get_test_run_id()
    )


def test_run_onehop_tests_from_registry():
    onehop_test = OneHopTestHarness()
    onehop_test.run(
        trapi_version="1.3",
        biolink_version="2.4.8",
        one=True
    )
    _report_outcome(
        "test_run_onehop_tests_from_registry",
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
        trapi_version="1.3",
        biolink_version="2.4.8",
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
