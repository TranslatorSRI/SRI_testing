from typing import Dict

from sri_testing.translator.sri.testing.report_db import TestReportDatabase, TestReport
from sri_testing.translator.sri.testing.onehops_test_runner import OneHopTestHarness

# For early testing of the Unit test, test data is not deleted when DEBUG is True;
# however, this interferes with idempotency of the tests (i.e. data must be manually deleted from the test database)
DEBUG: bool = False

SAMPLE_DOCUMENT_KEY: str = "test_run_summary"
SAMPLE_TEST_RESOURCE: str = "test_resource"
SAMPLE_DOCUMENT_TYPE = "Test Run Summary"
SAMPLE_ARA_ID: str = "arax"
UNKNOWN_ARA: str = "unknown_ara"
SAMPLE_KP_ID: str = "molepro"
UNKNOWN_KP: str = "unknown_kp"
SAMPLE_DOCUMENT: Dict = {
    "KP": {
        SAMPLE_KP_ID: {"some": "data"}
    },
    "ARA": {
        SAMPLE_ARA_ID: {
            "kps": {
                SAMPLE_KP_ID: {"some": "data"}
            }
        }
    }
}


def test_resource_filter():
    assert OneHopTestHarness.resource_filter(ara_id=SAMPLE_ARA_ID, kp_id=SAMPLE_KP_ID)(SAMPLE_DOCUMENT)
    unknown_ara: str = "unknown_ara"
    assert not OneHopTestHarness.resource_filter(ara_id=unknown_ara, kp_id=SAMPLE_KP_ID)(SAMPLE_DOCUMENT)
    unknown_kp: str = "unknown_kp"
    assert not OneHopTestHarness.resource_filter(ara_id=SAMPLE_ARA_ID, kp_id=unknown_kp)(SAMPLE_DOCUMENT)


def report_filter_test(test_report_db: TestReportDatabase, test_report: TestReport, test_run_id: str):
    assert test_run_id in test_report_db.get_available_reports(
        OneHopTestHarness.resource_filter(ara_id=SAMPLE_ARA_ID, kp_id=SAMPLE_KP_ID)
    ), f"Report '{test_run_id}' should be in available reports!"

    assert test_run_id not in test_report_db.get_available_reports(
        OneHopTestHarness.resource_filter(ara_id=UNKNOWN_ARA, kp_id=SAMPLE_KP_ID)
    ), f"Report '{test_run_id}' is not expected to be in available reports for the {UNKNOWN_ARA}!"

    assert test_run_id not in test_report_db.get_available_reports(
        OneHopTestHarness.resource_filter(ara_id=SAMPLE_ARA_ID, kp_id=UNKNOWN_KP)
    ), f"Report '{test_run_id}' is not expected to be in available reports for the {UNKNOWN_KP}!"

    if not DEBUG:
        test_report.delete()
        assert test_run_id not in test_report_db.get_available_reports()

        test_report_db.drop_database()
