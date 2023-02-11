import json

from os.path import sep
from datetime import datetime
from typing import Dict, Optional

from tests.onehop import get_test_results_dir
from sri_testing.translator.sri.testing.report_db import FileReportDatabase, TestReport
from . import (
    DEBUG,
    SAMPLE_DOCUMENT_KEY,
    SAMPLE_TEST_RESOURCE,
    SAMPLE_DOCUMENT_TYPE,
    SAMPLE_DOCUMENT,
    report_filter_test
)

TEST_DATABASE = "file-report-unit-test-database"


def test_create_file_report_database():

    frd = FileReportDatabase(db_name=TEST_DATABASE)

    assert TEST_DATABASE in frd.list_databases()

    assert any(['time_created' in doc for doc in frd.get_report_logs()])

    assert FileReportDatabase.LOG_NAME not in frd.get_available_reports()

    if not DEBUG:
        frd.drop_database()


def test_delete_file_report_db_database():
    # same as the previous test but ignoring DEBUG TO enforce the database deletion
    frd = FileReportDatabase(db_name=TEST_DATABASE)

    assert TEST_DATABASE in frd.list_databases()

    frd.drop_database()

    assert "test-database" not in frd.list_databases()


def sample_file_document_creation_and_insertion(
        frd: FileReportDatabase,
        identifier: str,
        is_big: bool = False
) -> TestReport:

    test_report: TestReport = frd.get_test_report(identifier=identifier)
    assert test_report.get_identifier() == identifier
    assert test_report.get_root_path() == f"{get_test_results_dir(frd.get_db_name())}{sep}{identifier}"

    # A test report is not yet available until something is saved
    assert identifier not in frd.get_available_reports()

    test_report.save_json_document(
        document_type=SAMPLE_DOCUMENT_TYPE,
        document=SAMPLE_DOCUMENT,
        document_key=SAMPLE_DOCUMENT_KEY,
        index=[SAMPLE_TEST_RESOURCE],
        is_big=is_big
    )
    assert identifier in frd.get_available_reports()
    # assert identifier in frd.get_available_reports(owner=SAMPLE_TEST_RESOURCE)

    return test_report


def _test_id(seq: int) -> str:
    return f"{datetime.now().strftime('%Y-%b-%d_%Hhr%M')}.{str(seq)}"


def test_create_test_report_then_save_and_retrieve_document():

    frd = FileReportDatabase(db_name=TEST_DATABASE)

    test_id = _test_id(1)

    test_report: TestReport = sample_file_document_creation_and_insertion(frd, test_id)

    document: Optional[Dict] = test_report.retrieve_document(
        document_type="test document", document_key=SAMPLE_DOCUMENT_KEY
    )
    assert document
    assert document["document_key"] == SAMPLE_DOCUMENT_KEY

    if not DEBUG:
        test_report.delete()
        assert test_id not in frd.get_available_reports()

        frd.drop_database()


def test_db_level_test_report_deletion():

    frd = FileReportDatabase(db_name=TEST_DATABASE)

    test_id = _test_id(2)

    test_report: TestReport = sample_file_document_creation_and_insertion(frd, test_id)

    frd.delete_test_report(test_report)
    assert test_id not in frd.get_available_reports()

    if not DEBUG:
        frd.drop_database()


def test_create_test_report_then_save_and_retrieve_a_big_document():

    frd = FileReportDatabase(db_name=TEST_DATABASE)

    test_id = _test_id(3)

    test_report: TestReport = sample_file_document_creation_and_insertion(frd, test_id, is_big=True)

    text_file: str = ""
    for line in test_report.stream_document(document_type="test document", document_key=SAMPLE_DOCUMENT_KEY):
        text_file += line

    assert text_file

    # Should be a JSON document
    document = json.loads(text_file)

    assert document["document_key"] == SAMPLE_DOCUMENT_KEY

    if not DEBUG:
        test_report.delete()
        assert test_id not in frd.get_available_reports()

        frd.drop_database()


def test_file_report_process_logger():

    frd = FileReportDatabase(db_name=TEST_DATABASE)

    test_id = _test_id(4)
    test_report: TestReport = frd.get_test_report(identifier=test_id)

    test_report.open_logger()
    test_report.write_logger("Hello World!")
    test_report.close_logger()

    # logs: List[Dict] = frd.get_report_logs()
    # assert logs
    # assert any(['time_created' in doc for doc in frd.get_report_logs()])


def test_get_available_reports_filter():
    frd = FileReportDatabase(db_name=TEST_DATABASE)

    test_run_id = _test_id(5)
    test_report: TestReport = sample_file_document_creation_and_insertion(frd, test_run_id)

    report_filter_test(frd, test_report, test_run_id)
