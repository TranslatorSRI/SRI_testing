"""
This test suite needs a running MongoDb instance (e.g. in Docker)
"""
import json
from typing import Dict, Optional
from sys import stderr
from os.path import sep
from datetime import datetime

from tests.onehop import get_test_results_dir
from translator.sri.testing.report_db import (
    TestReportDatabaseException,
    TestReport,
    MongoReportDatabase
)
from . import (
    DEBUG,
    SAMPLE_DOCUMENT_KEY,
    SAMPLE_TEST_RESOURCE,
    SAMPLE_DOCUMENT_TYPE,
    SAMPLE_DOCUMENT,
    SAMPLE_ARA_ID,
    UNKNOWN_ARA,
    SAMPLE_KP_ID,
    UNKNOWN_KP,
    sample_filter, report_filter_test
)

TEST_DATABASE = "mongo-report-unit-test-database"


def _test_run_id(seq: int) -> str:
    return f"{datetime.now().strftime('%Y-%b-%d_%Hhr%M')}.{str(seq)}"


def test_mongo_report_db_connection():
    try:
        mrd = MongoReportDatabase(db_name=TEST_DATABASE)

        assert TEST_DATABASE in mrd.list_databases()

        assert any(['time_created' in doc for doc in mrd.get_report_logs()])

        assert MongoReportDatabase.LOG_NAME not in mrd.get_available_reports()

        if not DEBUG:
            mrd.drop_database()

        print(
            "\nThe test_mongo_report_db_connection() connection has succeeded *as expected*... " +
            "The Test is a success!", file=stderr
        )
    except TestReportDatabaseException:
        assert False, "This test connection should succeed if a suitable Mongodb instance is running?!"


def test_delete_mongo_report_db_database():
    # same as the previous test but ignoring DEBUG TO enforce the database deletion
    try:
        mrd = MongoReportDatabase(db_name=TEST_DATABASE)

        assert TEST_DATABASE in mrd.list_databases()

        mrd.drop_database()

        assert TEST_DATABASE not in mrd.list_databases()

        print(
            "\nThe test_mongo_report_db_connection() connection has succeeded *as expected*... " +
            "The Test is a success!", file=stderr
        )
    except TestReportDatabaseException:
        assert False, "This test connection should succeed if a suitable Mongodb instance is running?!"


def test_fake_mongo_report_db_connection():
    try:
        MongoReportDatabase(
            user="nobody",
            password="nonsense",
            host="neverneverland"
        )
        assert False, "This nonsense test connection should always fail!"
    except TestReportDatabaseException:
        print(
            "\nThe test_fake_mongo_report_db_connection() fake connection has failed *as expected*... " +
            "The Test itself is a success!", file=stderr
        )
        assert True


def sample_mongodb_document_creation_and_insertion(
        mrd: MongoReportDatabase,
        test_run_id: str,
        is_big: bool = False
) -> TestReport:

    test_report: TestReport = mrd.get_test_report(identifier=test_run_id)
    assert test_report.get_identifier() == test_run_id, f"TestReport identifier should be {test_run_id}!"

    test_results_dir = get_test_results_dir(mrd.get_db_name())
    assert test_report.get_root_path() == f"{test_results_dir}{sep}{test_run_id}", "TestReport root path invalid!"

    # A test report is not yet available until something is saved
    assert test_run_id not in mrd.get_available_reports(), f"Report '{test_run_id}' should not be in available reports!"

    test_report.save_json_document(
        document_type=SAMPLE_DOCUMENT_TYPE,
        document=SAMPLE_DOCUMENT,
        document_key=SAMPLE_DOCUMENT_KEY,
        index=[SAMPLE_TEST_RESOURCE],
        is_big=is_big
    )
    assert test_run_id in mrd.get_available_reports(), f"Report '{test_run_id}' should be in available reports!"

    assert test_report.exists_document(SAMPLE_DOCUMENT_KEY), f"Document {SAMPLE_DOCUMENT_KEY} should exist!"

    return test_report


def test_create_test_report_then_save_and_retrieve_document():
    try:
        mrd = MongoReportDatabase(db_name=TEST_DATABASE)

        test_run_id = _test_run_id(1)
        test_report: TestReport = sample_mongodb_document_creation_and_insertion(mrd, test_run_id)

        document: Optional[Dict] = test_report.retrieve_document(
            document_type=SAMPLE_DOCUMENT_TYPE, document_key=SAMPLE_DOCUMENT_KEY
        )
        assert document
        assert document["document_key"] == SAMPLE_DOCUMENT_KEY

        if not DEBUG:
            test_report.delete()
            assert test_run_id not in mrd.get_available_reports(), "Stale report is still visible?"

            mrd.drop_database()

    except TestReportDatabaseException:
        assert False, "This test connection should succeed if a suitable Mongodb instance is running?!"


def test_db_level_test_report_deletion():

    try:
        mrd = MongoReportDatabase(db_name=TEST_DATABASE)

        test_run_id = _test_run_id(2)
        test_report: TestReport = sample_mongodb_document_creation_and_insertion(mrd, test_run_id)

        mrd.delete_test_report(test_report)
        assert test_run_id not in mrd.get_available_reports()

        if not DEBUG:
            mrd.drop_database()

    except TestReportDatabaseException:
        assert False, "This test document insertion should succeed if a suitable Mongodb instance is running?!"


def test_create_test_report_then_save_and_retrieve_a_big_document():
    try:
        mrd = MongoReportDatabase(db_name=TEST_DATABASE)

        test_run_id = _test_run_id(3)
        test_report: TestReport = sample_mongodb_document_creation_and_insertion(mrd, test_run_id, is_big=True)

        text_file: str = ""
        for line in test_report.stream_document(document_type=SAMPLE_DOCUMENT_TYPE, document_key=SAMPLE_DOCUMENT_KEY):
            text_file += line

        assert text_file

        # Should be a JSON document
        document = json.loads(text_file)

        assert document["document_key"] == SAMPLE_DOCUMENT_KEY

        if not DEBUG:
            test_report.delete()
            assert test_run_id not in mrd.get_available_reports()

            mrd.drop_database()

    except TestReportDatabaseException:
        assert False, "This test connection should succeed if a suitable Mongodb instance is running?!"


def test_mongo_report_process_logger():

    frd = MongoReportDatabase(db_name=TEST_DATABASE)

    test_run_id = _test_run_id(4)
    test_report: TestReport = frd.get_test_report(identifier=test_run_id)

    test_report.open_logger()
    test_report.write_logger("Hello World!")
    test_report.close_logger()

    # logs: List[Dict] = frd.get_report_logs()
    # assert logs
    # assert any(['time_created' in doc for doc in frd.get_report_logs()])


def test_sample_reports_filter():
    assert sample_filter(ara_id=SAMPLE_ARA_ID, kp_id=SAMPLE_KP_ID)(SAMPLE_DOCUMENT)
    unknown_ara: str = "unknown_ara"
    assert not sample_filter(ara_id=unknown_ara, kp_id=SAMPLE_KP_ID)(SAMPLE_DOCUMENT)
    unknown_kp: str = "unknown_kp"
    assert not sample_filter(ara_id=SAMPLE_ARA_ID, kp_id=unknown_kp)(SAMPLE_DOCUMENT)


def test_get_available_reports_filter():
    try:
        mrd = MongoReportDatabase(db_name=TEST_DATABASE)

        test_run_id = _test_run_id(3)
        test_report: TestReport = sample_mongodb_document_creation_and_insertion(mrd, test_run_id)

        report_filter_test(mrd, test_report, test_run_id)

    except TestReportDatabaseException:
        assert False, "This test connection should succeed if a suitable Mongodb instance is running?!"
