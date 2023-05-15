
from typing import Dict, Optional, List, IO, Generator, Callable
from sys import stderr
from os import environ, makedirs, listdir
from os.path import sep, normpath, exists
from time import sleep
import shutil
from datetime import datetime
from urllib.parse import quote_plus
from json import JSONEncoder, dump, dumps
import orjson

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, ConfigurationError

# for saving big MongoDb files
from gridfs import GridFS

from tests.onehop import TEST_RESULTS_DB, get_test_results_dir, ONEHOP_TEST_DIRECTORY

import logging


logger = logging.getLogger()
logger.setLevel("DEBUG")

RUNNING_INSIDE_DOCKER = environ.get('RUNNING_INSIDE_DOCKER', False)


class TestReportDatabaseException(RuntimeError):
    pass


class ReportJsonEncoder(JSONEncoder):
    def default(self, o):
        try:
            iterable = iter(o)
        except TypeError:
            pass
        else:
            return list(iterable)
        # Let the base class default method raise the TypeError
        return JSONEncoder.default(self, o)


class TestReportDatabase:

    LOG_NAME = "logs"

    """
    Abstract superclass of a Test Report Database
    """
    def __init__(self, db_name: Optional[str] = TEST_RESULTS_DB, **kwargs):
        self._db_name: str = db_name if db_name else TEST_RESULTS_DB
        self._test_results_path: str = get_test_results_dir(self.get_db_name())

    def get_db_name(self) -> str:
        return self._db_name

    def get_test_results_path(self) -> str:
        return self._test_results_path

    def list_databases(self) -> List[str]:
        raise NotImplementedError("Abstract method - implement in child subclass!")

    def drop_database(self):
        raise NotImplementedError("Abstract method - implement in child subclass!")

    def get_all_report_identifiers(self) -> List[str]:
        """
        Return all recorded report identifiers in the database, whether or not they are completed or available.
        :return: List[str] of all recorded report identifiers
        """
        raise NotImplementedError("Abstract method - implement in child subclass!")

    def get_available_reports(self, report_filter: Optional[Callable[[Dict], bool]] = None) -> List[str]:
        """
        Get (possibly filtered) list of identifiers of available reports from the TestReportDatabase.
        :param report_filter: Callable, filter that returns True if a Python object argument passes filter constraints
        :return: list of identifiers of available ('completed') reports.
        """
        completed_test_runs: List[str] = list()
        for identifier in self.get_all_report_identifiers():
            test_report: TestReport = self.get_test_report(identifier)
            # available TestReports *must* already have a test_run_summary.json document
            # Note that for the 'exists_document' method, the '.json' file extension is implied
            if test_report.exists_document("test_run_summary"):
                test_run_summary: Dict = test_report.retrieve_document("Summary", "test_run_summary")
                # We may further filter out TestReports based on the report_filter
                if report_filter is None or report_filter(test_run_summary):
                    completed_test_runs.append(identifier)
        return completed_test_runs

    def get_test_report(self, identifier):
        raise NotImplementedError("Abstract method - implement in child subclass!")

    def get_report_logs(self) -> List[Dict]:
        """
        :return: Dict, report database log (as a Python dictionary)
        """
        raise NotImplementedError("Abstract method - implement in child subclass!")

    def filter_document(self, document, ara_id: str, kp_id: str):
        pass


class TestReport:
    """
    Abstract superclass of a Test Report, which is a related
    collection of test run documents stored in a TestReportDatabase.
    """
    def __init__(self, identifier: str, database: TestReportDatabase):
        """
        TestReport constructor.

        :param identifier: report identifier (perhaps a timestamp?)
        :param database: TestReportDatabase to which the report belongs
        """
        assert identifier  # the test report 'identifier' should not be None or empty string
        self._report_identifier = identifier
        self._database = database
        self._report_root_path: Optional[str] = \
            f"{get_test_results_dir(self._database.get_db_name())}{sep}{identifier}"

    def get_identifier(self) -> str:
        return self._report_identifier

    def get_database(self) -> TestReportDatabase:
        return self._database

    def get_root_path(self) -> Optional[str]:
        return self._report_root_path

    def exists_document(self, document_key: str) -> bool:
        """
        :param document_key: str, document key identifier ('path')
        :return: True if exists
        """
        raise NotImplementedError("Abstract method - implement in child subclass!")

    def delete(self, ignore_errors: bool = False) -> True:
        """
        Delete internal representation of the TestReport.
        """
        # Signal deletion with an empty test report root path
        self._report_root_path = None
        return True

    def save_json_document(
            self,
            document_type: str,
            document: Dict,
            document_key: str,
            index: List[str],
            is_big: bool = False
    ):
        """
        Saves an indexed document either to a test report database or the filing system, indexed against owner resource.

        :param document_type: Dict, Python object to persist as a JSON document.
        :param document: Dict, Python object to persist as a JSON document.
        :param document_key: str, indexing path for the document being saved.
        :param index: List[str], list of InfoRes reference ('object') identifiers against which to index this document.
        :param is_big: bool, if True, flags that the JSON file is expected to require special handling due to its size.
        """
        raise NotImplementedError("Abstract method - implement in child subclass!")

    def retrieve_document(self, document_type: str, document_key: str) -> Optional[Dict]:
        """
        Retrieves a single report type of document, corresponding to a specified document key.

        :param document_type: str, name of report type simply used for informative error reporting.
        :param document_key: str, the key ('path') of the document being requested.
        :return: Dict, JSON document retrieved.
        """
        raise NotImplementedError("Abstract method - implement in child subclass!")

    def stream_document(self, document_type: str, document_key: str) -> Generator:
        """
        Retrieves a single report type of document, corresponding to a specified document key.

        :param document_type: str, name of report type simply used for informative error reporting.
        :param document_key: str, the key ('path') of the document being requested.
        :return: Generator, generator of streamed JSON document text
        """
        raise NotImplementedError("Abstract method - implement in child subclass!")

    def open_logger(self):
        raise NotImplementedError("Abstract method - implement in child subclass!")

    def write_logger(self, line: str):
        raise NotImplementedError("Abstract method - implement in child subclass!")

    def close_logger(self):
        raise NotImplementedError("Abstract method - implement in child subclass!")


###############################################################
# Deferred TestReportDatabase method creation to work around  #
# TestReportDatabase and TestReport forward definitions issue #
###############################################################
def _get_test_report(obj, identifier: str) -> TestReport:
    """
    :return: TestReport of the appropriate kind for the given type of TestReportDatabase
    """
    raise NotImplementedError("Abstract method - implement in child subclass!")


TestReportDatabase.get_test_report = _get_test_report


def _delete_test_report(obj, report: TestReport):
    """
    :param report: TestReport, to be deleted
    """
    raise NotImplementedError("Abstract method - implement in child subclass!")


TestReportDatabase.delete_test_report = _delete_test_report


class FileTestReport(TestReport):

    def __init__(self, identifier: str, database: TestReportDatabase):
        TestReport.__init__(self, identifier=identifier, database=database)

        # File system based reporting needs to create a
        # 'identifier' tagged directory for test results
        makedirs(self.get_database().get_test_results_path(), exist_ok=True)

        self._log_file: Optional[IO] = None

    def exists_document(self, document_key: str) -> bool:
        """
        :param document_key: str, document key identifier ('path')
        :return: True if exists
        """
        # sanity check: Posix key to equivalent OS directory path
        document_key = document_key.replace('/', sep)
        # Here, for the FileTestDatabase, we must explicitly add a '.json' file extension
        document_path = f"{self.get_root_path()}{sep}{document_key}.json"
        return exists(document_path)

    def delete(self, ignore_errors: bool = False) -> bool:
        """
        Delete internal representation of the FileTestReport.
        """
        try:
            # this single command does a good job of
            # deleting all the TestReport documents
            shutil.rmtree(self.get_root_path(), ignore_errors=ignore_errors)
            TestReport.delete(self)
        except OSError as ose:
            logger.warning(
                f"FileTestReport.delete():  could not delete '{str(self.get_root_path())}' report path: {str(ose)}"
            )
            if ignore_errors:
                return True
            else:
                return False

        # Signal success if no exception is thrown above...
        return True

    def get_absolute_file_path(self, document_key: str, create_path: bool = False) -> str:
        """
        Gets the absolute path of a given relative file path, creating the path of directories if indicated.

        :param document_key: str, the relative (Posix?) directory path for a given file
        :param create_path: bool, if True, then ensure that the intermediate directories of the path are created
        :return: str, absolute path of a given relative file path
        """
        absolute_file_path = normpath(f"{self.get_root_path()}{sep}{document_key}")
        if create_path:
            dir_path: str = sep.join(absolute_file_path.split(sep=sep)[:-1])
            try:
                makedirs(f"{dir_path}", exist_ok=True)
            except OSError as ose:
                logger.warning(
                    f"get_absolute_file_path() directory path '{dir_path}' could not be created? Exception: {str(ose)}"
                )
        return absolute_file_path

    def save_json_document(
            self,
            document_type: str,
            document: Dict,
            document_key: str,
            index: List[str],
            is_big: bool = False
    ):
        """
        Saves an indexed document either to a test report database or the filing system.

        :param document_type: Dict, Python object to persist as a JSON document.
        :param document: Dict, Python object to persist as a JSON document.
        :param document_key: str, indexing path for the document being saved.
        :param index: List[str], list of InfoRes reference ('object') identifiers against which to index this document.
        :param is_big: bool, if True, flags that the JSON file is expected to require special handling due to its size.
        """
        # for consistency relative to MongoTestReports, we add the document key to the document
        document["document_key"] = document_key

        document_path = self.get_absolute_file_path(document_key=document_key, create_path=True)
        try:
            # TODO: maybe I need to write 'is_big' files out as binary?
            with open(f"{document_path}.json", mode='xt', encoding='utf8', buffering=1, newline='\n') as document_file:
                dump(obj=document, fp=document_file, cls=ReportJsonEncoder, indent=4)
                document_file.flush()
            with open(f"{document_path}.json", mode='rt', encoding='utf8', buffering=1, newline='\n') as document_file:
                pass
        except OSError as ose:
            logger.warning(f"{document_type} '{document_key}' cannot be written out: {str(ose)}?")

    def retrieve_document(self, document_type: str, document_key: str) -> Optional[Dict]:
        """
        Retrieves a single report type of document, corresponding to a specified document key.

        :param document_type: str, name of report type simply used for informative error reporting.
        :param document_key: str, the key ('path') of the document being requested.
        :return: Dict, JSON document retrieved.
        """
        assert document_key
        document: Optional[Dict] = None
        document_path: str = self.get_absolute_file_path(document_key=document_key)
        try:
            with open(f"{document_path}.json", mode='r', encoding='utf8', buffering=1, newline='\n') as report_file:
                contents = report_file.read()
            if contents:
                document = orjson.loads(contents)
        except OSError as ose:
            logger.warning(f"{document_type} '{document_key}' is not (yet) accessible: {str(ose)}?")

        return document

    def stream_document(self, document_type: str, document_key: str) -> Generator:
        """
        Retrieves a single report type of document, corresponding to a specified document key.

        :param document_type: str, name of report type simply used for informative error reporting.
        :param document_key: str, the key ('path') of the document being requested.
        :return: Generator, generator of streamed JSON document text
        """
        document_path = self.get_absolute_file_path(document_key)
        try:
            with open(f"{document_path}.json", mode="rb") as datafile:
                data: bytes
                for data in datafile.readlines():
                    line: str = data.decode(encoding="utf8")
                    yield line.strip()
        except OSError as ose:
            logger.warning(f"{document_type} '{document_key}' is not (yet) accessible: {str(ose)}?")

    def open_logger(self):
        self._log_file: Optional[IO] = None
        if self.get_root_path():
            log_file_path: str = self.get_absolute_file_path(document_key="test.log", create_path=True)
            try:
                self._log_file = open(log_file_path, "w")
            except FileNotFoundError as fnfe:
                logger.warning(f"Cannot open log file: {str(fnfe)}")
        else:
            logger.warning(f"ProcessLogger(): 'log_file_path' is not set. No process logging shall be done.")

    def write_logger(self, line: str):
        if self._log_file:
            self._log_file.write(line)

            # Will this help log performance?
            self._log_file.flush()

    def close_logger(self):
        if self._log_file:
            self._log_file.flush()
            self._log_file.close()
            self._log_file = None


class FileReportDatabase(TestReportDatabase):
    """
    Wrapper class for an OS filing system-based repository for storing and retrieving SRI Testing test results.
    """

    def __init__(self, db_name: Optional[str] = None, **kwargs):
        TestReportDatabase.__init__(self, db_name=db_name, **kwargs)

        # File system based reporting needs to create
        # a db_name'd root directory for test results
        makedirs(self.get_test_results_path(), exist_ok=True)

        self._logs: str = normpath(f"{self.get_test_results_path()}{sep}{self.LOG_NAME}")
        makedirs(self._logs, exist_ok=True)

        creation_log_file: str = f"{self._logs}{sep}creation.json"
        if not exists(creation_log_file):
            time_created: str = datetime.now().strftime("%Y-%b-%d_%Hhr%M")
            document = {"time_created": time_created}
            try:
                with open(creation_log_file, mode='w', encoding='utf8', buffering=1, newline='\n') as log_file:
                    dump(obj=document, fp=log_file, indent=4)
            except OSError as ose:
                logger.warning(f"'{creation_log_file}' cannot be written out: {str(ose)}?")

    def list_databases(self) -> List[str]:
        # At present, the FileReportDatabase hosts all of its
        # 'databases' a.k.a. 'db_name' folders, under the ONEHOP_TEST_DIRECTORY
        return [identifier for identifier in listdir(ONEHOP_TEST_DIRECTORY)]

    def drop_database(self):
        shutil.rmtree(self.get_test_results_path())

    def get_test_report(self, identifier: str) -> TestReport:
        """
        :param identifier: str, test run identifier for the report
        :return: wrapped test report
        """
        report = FileTestReport(identifier=identifier, database=self)
        return report

    @staticmethod
    def delete_test_report(report: TestReport):
        """
        :param report: TestReport to be deleted
        """
        report.delete()

    def get_all_report_identifiers(self) -> List[str]:
        test_results_directory = self.get_test_results_path()
        return listdir(test_results_directory)

    def get_report_logs(self) -> List[Dict]:
        """
        :return: Dict, report database log (as a Python dictionary)
        """
        logs: List[Dict] = list()
        for identifier in listdir(self._logs):
            try:
                log_file_name = f"{self._logs}{sep}{identifier}"
                with open(log_file_name, mode='r', encoding='utf8', buffering=1, newline='\n') as log_file:
                    contents = log_file.read()
                if contents:
                    document: Dict = orjson.loads(contents)
                    logs.append(document)
            except OSError as ose:
                logger.warning(f"Log file '{identifier}' cannot be read in: {str(ose)}?")
        return logs


class MongoTestReport(TestReport):

    def __init__(self, identifier: str, database: TestReportDatabase, mongo_db: Database):

        TestReport.__init__(self, identifier=identifier, database=database)

        # remember the MongoDb database handle associated with this MongoTestReport
        self._db: Database = mongo_db

        # Also save large files into GridFS
        self._gridfs: GridFS = GridFS(self._db, collection=identifier)

        # MongoDb based reporting needs to create a
        # 'identifier' tagged collection for test results
        self._collection: Optional[Collection] = self._db[identifier]

    def exists_document(self, document_key: str) -> bool:
        return self._collection.find_one(filter={'document_key': document_key}) is not None

    def delete(self, ignore_errors: bool = False) -> bool:
        """
        Delete internal representation of the MongoTestReport.
        :return: bool, True is successful
        """
        try:
            # MongoTestReport deletion is a bit more complex
            # given that we have stored "big" documents in GridFS,
            # not in MongoDb itself. Thus, we also need to purge
            # the GridFS database of the associated GridFS collections.
            test_run_id = self.get_identifier()
            gridfs_files = f"{test_run_id}.files"
            gridfs_chunks = f"{test_run_id}.chunks"
            # we briefly sleep to yield to the system
            # to allow the MongoDb task to complete
            self._db.drop_collection(gridfs_files)
            sleep(1)
            self._db.drop_collection(gridfs_chunks)
            sleep(1)
            self._db.drop_collection(test_run_id)
            TestReport.delete(self)
            self._collection = None
        except Exception as exc:
            logger.warning(
                f"MongoTestReport.delete():  could not delete '{str(self.get_root_path())}' report path: {str(exc)}"
            )
            if ignore_errors:
                return True
            else:
                return False

        # Signal success if no exception is thrown above...
        return True

    def save_json_document(
            self,
            document_type: str,
            document: Dict,
            document_key: str,
            index: List[str],
            is_big: bool = False
    ):
        """
        Saves an indexed document either to a test report database or the filing system.

        :param document_type: Dict, Python object to persist as a JSON document.
        :param document: Dict, Python object to persist as a JSON document.
        :param document_key: str, indexing path for the document being saved.
        :param index: List[str], list of InfoRes reference ('object') identifiers against which to index this document.
        :param is_big: bool, if True, flags that the JSON file is expected to require special handling due to its size.
        """
        # Persist index test run result JSON document suitably indexed by
        # the document_key, into the (wrapped MongoDb) TestReportDatabase
        document['document_key'] = document_key

        # sanity check: In case we are attempting to save a BSON document that
        # was previously saved/retrieved in Mongo, we should delete any _id field
        # and (stale) ObjectId value, since the latter is not JSON serializable
        if '_id' in document:
            document.pop('_id')

        if is_big:
            # Save this large document with GridFS
            gridfs_uid = self._gridfs.put(dumps(obj=document, cls=ReportJsonEncoder), encoding="utf8")
            # we save large documents in GridFS dereferenced by a proxy document in the main database
            proxy_document = {
                'document_key': document_key,
                'gridfs_uid': gridfs_uid
            }
            self._collection.insert_one(proxy_document)
        else:
            self._collection.insert_one(document)

    def retrieve_document(self, document_type: str, document_key: str) -> Optional[Dict]:
        """
        Retrieves a single report type of document, corresponding to a specified document key.

        :param document_type: str, name of report type simply used for informative error reporting.
        :param document_key: str, the key ('path') of the document being requested.
        :return: Dict, JSON document retrieved.
        """
        assert document_key
        assert self._collection is not None
        document: Optional[Dict] = self._collection.find_one(
            filter={'document_key': document_key}, projection={'_id': False}
        )
        return document

    def stream_document(self, document_type: str, document_key: str) -> Generator:
        """
        Retrieves a single report type of document, corresponding to a specified document key

        :param document_type: str, name of report type simply used for informative error reporting.
        :param document_key: str, the key ('path') of the document being requested.
        :return: Generator, generator of streamed JSON document text
        """
        # For reasons of file size scalability, we assume that the document was large and stored in GridFS
        document_proxy: Optional[Dict] = self._collection.find_one({'document_key': document_key})
        if document_proxy:
            gridfs_uid = document_proxy["gridfs_uid"]
            try:
                with self._gridfs.get(gridfs_uid) as datafile:
                    yield datafile.readline().decode(encoding="utf8")
            except OSError as ose:
                logger.warning(f"{document_type} '{document_key}' is not (yet) accessible: {str(ose)}?")

    def open_logger(self):
        # raise NotImplementedError("Implement me!")
        pass

    def write_logger(self, line: str):
        # raise NotImplementedError("Implement me!")
        pass

    def close_logger(self):
        # raise NotImplementedError("Implement me!")
        pass


class MongoReportDatabase(TestReportDatabase):

    NON_SYSTEM_COLLECTION_FILTER: Dict = {
        "name": {"$regex": rf"^(?!system\.|{TestReportDatabase.LOG_NAME}|fs\..*|test_.*|.*\.files|.*\.chunks)"}
    }

    """
    Wrapper class for a MongoDb instance-based repository for storing and retrieving SRI Testing test results.
    """
    def __init__(
            self,
            db_name: Optional[str] = None,
            user: str = environ.get('MONGO_INITDB_ROOT_USERNAME', "root"),
            password: str = environ.get('MONGO_INITDB_ROOT_PASSWORD', "example"),
            host: str = environ.get('MONGO_INITDB_HOST', "localhost"),
            **kwargs
    ):
        """
        TestReportDatabase constructor.

        :param user: str, MongoDb user (default: 'MONGO_INITDB_ROOT_USERNAME' or "root")
        :param password:  str, MongoDb password (default: 'MONGO_INITDB_ROOT_PASSWORD' or "example")
        :param host:  str, MongoDb host (default: "mongo" if inside the SRI Testing docker container else "localhost")
        :param db_name:  str, name of database (default: "sri_testing")
        :param kwargs:

        :raises MongoReportException
        """
        TestReportDatabase.__init__(self, db_name=db_name, **kwargs)

        self._db_uri = "mongodb://%s:%s@%s" % (quote_plus(user), quote_plus(password), host)
        try:
            self._db_client = MongoClient(
                host=self._db_uri,  # host: Optional[Union[str, Sequence[str]]] = None,
                port=27017,  # port: Optional[int] = None,
                # document_class: Optional[Type[_DocumentType]] = None,
                # tz_aware: Optional[bool] = None,
                # connect: Optional[bool] = None,
                # type_registry: Optional[TypeRegistry] = None,
                # **kwargs: Any,
            )

            # 'ping' will throw a pymongo.errors.ConnectionFailure if the connection fails
            self._db_client.admin.command('ping')
        except (ConnectionFailure, ConnectionError, ServerSelectionTimeoutError, ConfigurationError) as mrd_ce:
            err_msg = f"MongoReportDatabase connection error: {str(mrd_ce)}"
            logger.error(err_msg)
            raise TestReportDatabaseException(err_msg)

        self._mongo_db: Database = self._db_client[self._db_name]

        if self.LOG_NAME not in self._mongo_db.list_collection_names():
            time_created: str = datetime.now().strftime("%Y-%b-%d_%Hhr%M")
            self._logs: Collection = self._mongo_db[self.LOG_NAME]
            # this should create the log once
            self._logs.insert_one({"time_created": time_created})
        else:
            self._logs: Collection = self._mongo_db[self.LOG_NAME]

    def list_databases(self) -> List[str]:
        return [name for name in self._db_client.list_database_names() if name not in ['admin', 'config', 'local']]

    def drop_database(self):
        if self._db_name:
            self._db_client.drop_database(self._db_name)
            self._db_name = None

    def get_test_report(self, identifier: str) -> TestReport:
        """
        :param identifier: str, test run identifier for the report
        :return: wrapped test report
        """
        report = MongoTestReport(identifier=identifier, database=self, mongo_db=self._mongo_db)
        return report

    @staticmethod
    def delete_test_report(report: TestReport):
        """
        :param report: TestReport to be deleted (should be an instance of MongoTestReport)
        """
        assert isinstance(report, MongoTestReport)
        report.delete()

    def get_all_report_identifiers(self) -> List[str]:
        return self._mongo_db.list_collection_names(filter=self.NON_SYSTEM_COLLECTION_FILTER)

    def get_report_logs(self) -> List[Dict]:
        """
        :return: Dict, report database log (as a Python dictionary)
        """
        logs: List[Dict] = [doc for doc in self._logs.find()]
        return logs


####################################################################
# Here we globally configure and bind a singleton TestReportDatabase
####################################################################
_test_report_database: Optional[TestReportDatabase] = None


def get_test_report_database(use_file_database_as_default: bool = False) -> TestReportDatabase:
    global _test_report_database
    if not _test_report_database:
        if not use_file_database_as_default:
            try:
                # TODO: we only use 'default' MongoDb connection settings here. Needs to be parameterized...
                _test_report_database = MongoReportDatabase()
                print("Using MongoReportDatabase!", file=stderr)
            except TestReportDatabaseException:
                logger.warning("Mongodb instance not running? We will use a local FileReportDatabase instead...")
                _test_report_database = FileReportDatabase()
                print("Using FileReportDatabase!", file=stderr)
        else:
            _test_report_database = FileReportDatabase()
            print("Using FileReportDatabase as the default!", file=stderr)

    return _test_report_database
