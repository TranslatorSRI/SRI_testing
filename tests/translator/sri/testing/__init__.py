from typing import Dict

from translator.sri.testing.report_db import TestReportDatabase, TestReport

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


def sample_filter(ara_id: str, kp_id: str):

    def filter_function(document: Dict) -> bool:
        if "ARA" in document:
            ara_data: Dict = document["ARA"]
            if ara_id not in ara_data:
                return False
            else:
                ara_data = ara_data[ara_id]
                if "kps" not in ara_data:
                    return False
                else:
                    kp_data = ara_data["kps"]
                    if kp_id and kp_id not in kp_data:
                        return False

        if "KP" in document:
            kp_data = document["KP"]
            if kp_id not in kp_data:
                return False
        return True

    return filter_function


def report_filter_test(test_report_db: TestReportDatabase, test_report: TestReport, test_run_id: str):
    assert test_run_id in test_report_db.get_available_reports(
        sample_filter(ara_id=SAMPLE_ARA_ID, kp_id=SAMPLE_KP_ID)
    ), f"Report '{test_run_id}' should be in available reports!"

    assert test_run_id not in test_report_db.get_available_reports(
        sample_filter(ara_id=UNKNOWN_ARA, kp_id=SAMPLE_KP_ID)
    ), f"Report '{test_run_id}' is not expected to be in available reports for the {UNKNOWN_ARA}!"

    assert test_run_id not in test_report_db.get_available_reports(
        sample_filter(ara_id=SAMPLE_ARA_ID, kp_id=UNKNOWN_KP)
    ), f"Report '{test_run_id}' is not expected to be in available reports for the {UNKNOWN_KP}!"

    if not DEBUG:
        test_report.delete()
        assert test_run_id not in test_report_db.get_available_reports()

        test_report_db.drop_database()
