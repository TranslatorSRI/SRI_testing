from os.path import sep
from datetime import datetime
from tests.onehop import TEST_RESULTS_DB, ONEHOP_TEST_DIRECTORY
from sri_testing.translator.sri.testing.report_db import TestReportDatabase, TestReport

TEST_DATABASE = "test-database"


def test_default_test_report_database_creation():
    trd = TestReportDatabase()
    assert trd.get_db_name() == TEST_RESULTS_DB
    assert trd.get_test_results_path() == f"{ONEHOP_TEST_DIRECTORY}{sep}{TEST_RESULTS_DB}"


def test_named_test_report_database_creation():
    trd = TestReportDatabase(db_name=TEST_DATABASE)
    assert trd.get_db_name() == "test-database"
    assert trd.get_test_results_path() == f"{ONEHOP_TEST_DIRECTORY}{sep}test-database"


def test_test_report_creation():

    trd = TestReportDatabase(db_name=TEST_DATABASE)

    test_id = datetime.now().strftime("%Y-%b-%d_%Hhr%M")
    test_report = TestReport(identifier=test_id, database=trd)

    assert test_report.get_identifier() == test_id
    assert test_report.get_database() == trd
    assert test_report.get_root_path() == f"{ONEHOP_TEST_DIRECTORY}{sep}test-database{sep}{test_id}"
