"""
Configure one hop tests
"""
from typing import Optional, Union, List, Set, Dict, Any
from sys import stderr
from os import path, walk, sep
from collections import defaultdict

import json

import logging

from deprecation import deprecated
from pytest_harvest import get_session_results_dct

from reasoner_validator.biolink import check_biolink_model_compliance_of_input_edge, BiolinkValidator
from reasoner_validator.versioning import latest

from translator.registry import (
    get_remote_test_data_file,
    get_the_registry_data,
    extract_component_test_metadata_from_registry
)

from translator.trapi import generate_edge_id, DEFAULT_TRAPI_VERSION, UnitTestReport

from tests.onehop import util as oh_util
from tests.onehop.util import (
    get_unit_test_codes, get_unit_test_list
)
from translator.sri.testing.onehops_test_runner import (
    OneHopTestHarness,
    parse_unit_test_name
)

logger = logging.getLogger(__name__)


# TODO: temporary circuit breaker for huge edge test data sets
REASONABLE_NUMBER_OF_TEST_EDGES: int = 100


def _new_kp_test_case_summary(trapi_version: str, biolink_version: str) -> Dict[str, Union[int, str, Dict]]:
    """
    Initialize a dictionary to capture statistics for a single KP test case summary.

    :param trapi_version: str, TRAPI version associated with the test case (SemVer)
    :param biolink_version:  str, Biolink Model version associated with the test case (SemVer)

    :return: Dict[str, Union[int, str, Dict]], initialized
    """
    new_test_case_summary: Dict[str, Union[int, str, Dict]] = {
        'no_of_edges': 0,
        'trapi_version': trapi_version,
        'biolink_version': biolink_version,
        'results': dict()
    }
    return new_test_case_summary


def _new_kp_resource_summary(trapi_version: str, biolink_version: str) -> Dict[str, Union[str, Dict]]:
    """
    Initialize a dictionary to capture statistics for a single KP test case summary.

    :param trapi_version: str, TRAPI version associated with the test case (SemVer)
    :param biolink_version:  str, Biolink Model version associated with the test case (SemVer)

    :return: Dict[str, Union[int, str, Dict]], initialized
    """
    new_test_case_summary: Dict[str, Union[str, Dict]] = {
        'trapi_version': trapi_version,
        'biolink_version': biolink_version,
        'test_edges': dict()
    }
    return new_test_case_summary


def _new_unit_test_statistics() -> Dict[str, int]:
    """
    Initialize a dictionary to capture statistics for a single unit test category.

    :return: Dict[int] initialized
    """
    new_stats: Dict[str, int] = {
        'passed': 0,
        'failed': 0,
        'skipped': 0,
        # might add 'warning' and 'info' tallies in the future?
        # 'warning': 0,
        # 'info': 0,
    }
    return new_stats


def _tally_unit_test_result(test_case_summary: Dict, test_id: str, edge_num: int, test_result: str):

    # Sanity checks...
    assert 'results' in test_case_summary, "Missing results in summary?"

    assert test_id in get_unit_test_list(), \
        f"Invalid test_result '{str(test_result)}'"
    assert test_result in ['passed', 'failed', 'skipped', 'warning', 'info'], \
        f"Invalid test_result '{str(test_result)}'"

    while edge_num + 1 > test_case_summary['no_of_edges']:
        test_case_summary['no_of_edges'] += 1

    results = test_case_summary['results']
    if test_id not in results:
        results[test_id] = _new_unit_test_statistics()

    results[test_id][test_result] += 1


##########################################################################################
# JSON Test Reports are emitted in this pytest_sessionfinish() postprocessor as follows:
#
# 1. Test Summary:  summary statistics of entire test run, indexed by ARA and KP resources
# 2. Resource Summary: ARA or KP level summary across all edges
# 3. Edge Details: details of test results for one edge in a given resource test dataset
# 4. Response: TRAPI JSON response message (may be huge; use file streaming to access!)
##########################################################################################

# Selective list of Resource Summary fields
RESOURCE_SUMMARY_FIELDS = [
    "subject_category",
    "object_category",
    "predicate",
    "subject",
    "object"
]


def pytest_sessionfinish(session):
    """ Gather all results and save them to a csv.
    Works both on worker and master nodes, and also with xdist disabled
    """
    # test_run_id may not be set (i.e. may be 'None'),
    # in which case, a OneHopTestHarness test run
    # object is, instantiated with a 'fake' test_run_id
    test_run: OneHopTestHarness = OneHopTestHarness(
        session.config.option.test_run_id
        if "test_run_id" in session.config.option and session.config.option.test_run_id else None
    )

    session_results = get_session_results_dct(session)

    test_run_summary: Dict = dict()
    resource_summaries: Dict = dict()
    case_details: Dict = dict()

    for unit_test_key, details in session_results.items():

        rb: Dict = details['fixtures']['results_bag']

        # sanity check: clean up MS Windoze EOL characters, when present in results_bag keys
        rb = {key.strip("\r\n"): value for key, value in rb.items()}

        # Sanity check? Missing 'case' would seem like an SRI Testing logical bug?
        assert 'case' in rb
        test_case = rb['case']

        # clean up the name for safe file system usage
        component, ara_id, kp_id, edge_num, test_id, edge_details_key = parse_unit_test_name(
            unit_test_key=unit_test_key
        )

        # Sanity check: missing 'url' is likely a logical bug in SRI Testing?
        assert 'url' in test_case
        url: str = test_case['url']

        # Sanity check: missing TRAPI version is likely a logical bug in SRI Testing?
        assert 'trapi_version' in test_case
        trapi_version: Optional[str] = test_case['trapi_version']

        # Sanity check: missing Biolink Model version is likely a logical bug in SRI Testing?
        assert 'biolink_version' in test_case
        biolink_version: Optional[str] = test_case['biolink_version']

        ##############################################################
        # Summary file indexed by component, resources and edge cases
        ##############################################################
        if component not in test_run_summary:
            test_run_summary[component] = dict()

            # Set up indexed resource summaries in parallel
            resource_summaries[component] = dict()

        case_summary: Dict
        if ara_id:
            if ara_id not in test_run_summary[component]:
                test_run_summary[component][ara_id] = dict()
                test_run_summary[component][ara_id]['url'] = url
                test_run_summary[component][ara_id]['test_data_location'] = test_case['ara_test_data_location']
                test_run_summary[component][ara_id]['kps'] = dict()

                resource_summaries[component][ara_id] = dict()

            if kp_id not in test_run_summary[component][ara_id]['kps']:
                test_run_summary[component][ara_id]['kps'][kp_id] = _new_kp_test_case_summary(
                    trapi_version=trapi_version,
                    biolink_version=biolink_version
                )
                resource_summaries[component][ara_id][kp_id] = _new_kp_resource_summary(
                    trapi_version=trapi_version,
                    biolink_version=biolink_version
                )

            case_summary = test_run_summary[component][ara_id]['kps'][kp_id]
            resource_summary = resource_summaries[component][ara_id][kp_id]

        else:
            if kp_id not in test_run_summary[component]:
                test_run_summary[component][kp_id] = _new_kp_test_case_summary(
                    trapi_version=trapi_version,
                    biolink_version=biolink_version
                )
                test_run_summary[component][kp_id]['url'] = url
                test_run_summary[component][kp_id]['test_data_location'] = test_case['kp_test_data_location']

                resource_summaries[component][kp_id] = _new_kp_resource_summary(
                    trapi_version=trapi_version,
                    biolink_version=biolink_version
                )

            case_summary = test_run_summary[component][kp_id]
            resource_summary = resource_summaries[component][kp_id]

        # Tally up the number of test results of a given 'status' across 'test_id' unit test categories
        _tally_unit_test_result(case_summary, test_id, edge_num, details['status'])

        # TODO: merge case details here into a Cartesian product table of edges
        #       and unit test id's for a given resource indexed by ARA and KP
        idx: str = str(test_case['idx'])

        if idx not in resource_summary['test_edges']:
            resource_summary['test_edges'][idx] = {
                'test_data': dict(),
                'results': dict()
            }

        for field in RESOURCE_SUMMARY_FIELDS:
            if field not in resource_summary['test_edges'][idx]['test_data'] and field in test_case:
                resource_summary['test_edges'][idx]['test_data'][field] = test_case[field]

        if test_id not in resource_summary['test_edges'][idx]['results']:
            resource_summary['test_edges'][idx]['results'][test_id] = dict()
        resource_summary['test_edges'][idx]['results'][test_id]['outcome'] = details['status']

        test_report: UnitTestReport = rb['unit_test_report']
        if test_report and test_report.has_messages:
            resource_summary['test_edges'][idx]['results'][test_id]['validation'] = test_report.get_messages()

        ###################################################
        # Full test details will still be indexed by edge #
        ###################################################
        if edge_details_key not in case_details:

            # TODO: this is a bit memory intensive... may need a
            #       better strategy for saving some of the details?
            case_details[edge_details_key] = dict()

            if 'case' in rb and 'case' not in case_details[edge_details_key]:
                case_details[edge_details_key] = test_case

            if 'results' not in case_details[edge_details_key]:
                case_details[edge_details_key]['results'] = dict()

        if test_id not in case_details[edge_details_key]['results']:
            case_details[edge_details_key]['results'][test_id] = dict()

        test_details = case_details[edge_details_key]['results'][test_id]

        # Replicating 'PASSED, FAILED, SKIPPED' test status
        # for each unit test, here in the detailed report
        test_details['outcome'] = details['status']

        # Capture more request/response details for test failures
        if details['status'] == 'failed':

            if 'request' in rb:
                # TODO: maybe the 'request' document could be persisted
                #       separately JIT, to avoid using too much RAM?
                test_details['request'] = rb['request']
            else:
                test_details['request'] = "No 'request' generated for this unit test?"

            if 'response' in rb:
                case_response: Dict = dict()
                case_response['url'] = test_case['url'] if 'url' in test_case else "Unknown?!"
                case_response['unit_test_key'] = unit_test_key
                case_response['http_status_code'] = rb["response"]["status_code"]
                case_response['response'] = rb['response']['response_json']

                response_document_key = f"{edge_details_key}-{test_id}"
                test_run.save_json_document(
                    document_type="TRAPI I/O",
                    document=case_response,
                    document_key=response_document_key,
                    is_big=True
                )

            else:
                test_details['response'] = "No 'response' generated for this unit test?"

        # TODO: in principle, with a database, we could now simply update
        #       the 'test_details' document here, updated with the
        #       just encountered test result, rather than cache it in RAM
        #       then defer writing it out later below, once it is complete?

    # TODO: it would be nice to avoid compiling the case_details dictionary in RAM, for later saving,
    #       but this currently seems *almost* unavoidable, for the aggregated details file document?
    #       By "almost", one means that a document already written out could be read back into memory
    #       then updated, but if one is doing this, why not rather use a (document) database?
    #
    # Save the cached details of each edge test case
    for edge_details_key in case_details:
        test_run.save_json_document(
            document_type="Details",
            document=case_details[edge_details_key],
            document_key=edge_details_key
        )

    #
    # Save the various resource test summaries
    #
    # All KP's individually
    if "KP" in resource_summaries:
        kp_summaries = resource_summaries["KP"]
        for kp in kp_summaries:
            # Save Test Run Summary
            document_key: str = f"KP/{kp}/resource_summary"
            test_run.save_json_document(
                document_type="Direct KP Summary",
                document=kp_summaries[kp],
                document_key=document_key
            )

    # All KP's called by ARA's
    if "ARA" in resource_summaries:
        ara_summaries = resource_summaries["ARA"]
        for ara in ara_summaries:
            for kp in ara_summaries[ara]:
                # Save embedded KP Resource Summary
                document_key: str = f"ARA/{ara}/{kp}/resource_summary"
                test_run.save_json_document(
                    document_type="ARA Embedded KP Summary",
                    document=ara_summaries[ara][kp],
                    document_key=document_key
                )

    # Save Test Run Summary
    test_run.save_json_document(
        document_type="Test Run Summary",
        document=test_run_summary,
        document_key="test_run_summary"
    )


def pytest_addoption(parser):
    """
    :param parser:
    """
    parser.addoption("--teststyle", action="store", default='all', help='Which Test to Run?')
    parser.addoption("--one", action="store_true", help="Only use first edge from each KP file")
    parser.addoption(
        "--triple_source", action="store", default='REGISTRY',  # 'test_triples/KP',
        help="'REGISTRY', directory or file from which to retrieve triples (Default: 'REGISTRY', which triggers " +
             "the use of metadata, in KP entries from the Translator SmartAPI Registry, to configure the tests)."
    )
    parser.addoption(
        "--ARA_source", action="store", default='REGISTRY',  # 'test_triples/ARA',
        help="'REGISTRY', directory or file from which to retrieve ARA Config (Default: 'REGISTRY', which triggers " +
             "the use of metadata, in ARA entries from the Translator SmartAPI Registry, to configure the tests)."
    )
    # We hard code a 'current' version (1.2 as of March 2022)
    # but we'll eventually use an endpoint's SmartAPI published value 'x-trapi' published metadata value
    parser.addoption(
        "--TRAPI_Version", action="store", default=None,
        help='TRAPI API Version to use for the tests '
             '(Default: latest public release or REGISTRY metadata value).'
    )
    # We could eventually use a TRAPI/meta_knowledge_graph 'x-translator' published metadata value,
    # but we'll use the Biolink Model Toolkit default for now?
    parser.addoption(
        "--Biolink_Version", action="store", default=None,
        help='Biolink Model Version to use for the tests ' +
             '(Default: latest Biolink Model Toolkit default or REGISTRY metadata value).'
    )
    #  Mostly used when the SRI Testing harness is run by a web service
    parser.addoption(
        "--test_run_id", action="store", default="",
        help='Optional Test Run Identifier for internal use to index test results.'
    )


def _fix_path(file_path: str) -> str:
    """
    Fixes OS specific path string issues (especially, for MS Windows)
    
    :param file_path: file path to be repaired
    """
    file_path = file_path.replace("\\", "/")
    return file_path


def _build_filelist(entry):
    filelist = []
    if path.isfile(entry):
        filelist.append(entry)
    else:
        dtrips = walk(entry)
        for dirpath, dirnames, filenames in dtrips:
            # SKIP specific test folders, if so tagged
            if dirpath and dirpath.endswith("SKIP"):
                continue
            # Windows OS quirk - fix path
            real_dirpath = _fix_path(dirpath)
            for f in filenames:
                # SKIP specific test files, if so tagged
                if f.endswith("SKIP"):
                    continue
                kpfile = f'{real_dirpath}{sep}{f}'
                filelist.append(kpfile)
    
    return filelist


def get_test_data_sources(
        source: str,
        component_type: str,
        trapi_version: Optional[str] = None,
        biolink_version: Optional[str] = None
) -> Dict[str, Dict[str, Optional[str]]]:
    """
    Retrieves a dictionary of metadata of 'component_type', indexed by name.

    If the 'source' is specified to be the string 'REGISTRY', then
    this dictionary is populated from the Translator SmartAPI Registry,
    using published 'test_data_location' values as keys.

    Otherwise, a local file source of the metadata is assumed,
    using the local data file name as a key (these should be unique).

    :param source: str, specific remote or local source from which the test data sources are to be retrieved.
    :param component_type: str, component type 'KP' or 'ARA'
    :param trapi_version: SemVer caller override of TRAPI release target for validation (Default: None)
    :param biolink_version: SemVer caller override of Biolink Model release target for validation (Default: None)

    :return: Dict[str, Dict[str, Optional[str]]], service metadata dictionary
    """
    service_metadata: Dict[str, Dict[str, Optional[str]]]

    if source == "REGISTRY":
        # Access service metadata from the Translator SmartAPI Registry,
        # indexed using the "test_data_location" field as the unique key
        registry_data: Dict = get_the_registry_data()
        service_metadata = extract_component_test_metadata_from_registry(registry_data, component_type)
    else:
        # Access local set of test data triples
        if not path.exists(source):
            print("No such location:", source, flush=True, file=stderr)
            return dict()

        filelist: List[str] = _build_filelist(source)

        # Create an empty "mock" service metadata structure
        # indexed using the local file name as the unique key
        # We will try to populate this metadata later, from
        # the file contents or from default test conditions

        # Note: local templates don't specify their
        # TRAPI and Biolink Model versions.
        # The code later retrieves the default BMT
        # Biolink Model version so None is ok here,
        # however, TRAPI does need to be set here
        metadata_template = {
            "service_title": None,
            "service_version": None,
            "component": component_type,
            "infores": None,
            "biolink_version": None,
            "trapi_version": latest.get(DEFAULT_TRAPI_VERSION)
        }
        service_metadata = {name: metadata_template.copy() for name in filelist}

    # Possible CLI override of the metadata value of
    # TRAPI and/or Biolink Model releases used for data validation
    if trapi_version:
        for service_name in service_metadata.keys():
            service_metadata[service_name]['trapi_version'] = latest.get(trapi_version)

    if biolink_version:
        for service_name in service_metadata.keys():
            service_metadata[service_name]['biolink_version'] = biolink_version

    return service_metadata


def load_test_data_source(
        source: str,
        metadata: Dict[str, Optional[str]]
) -> Optional[Dict]:
    """
    Load one specified component test data source.

    :param source: source string, URL if from "remote"; file path if local
    :param metadata: metadata associated with source
    :return: json test data with (some) metadata; 'None' if unavailable
    """
    # sanity check
    assert metadata is not None

    if not source.endswith('json'):
        # Source file, whatever its origin -
        # local or Translator SmartAPI Registry x-trapi
        # specified test_data_location - should be a JSON file.
        # Ignore this test data source...
        return None

    test_data: Optional[Dict] = None
    if source.startswith('http'):
        # Source is an online test data repository, likely harvested
        # from the Translator SmartAPI Registry 'test_data_location'
        test_data = get_remote_test_data_file(source)
    else:
        # Source is a local data file
        with open(source, 'r') as local_file:
            try:
                test_data = json.load(local_file)
            except (json.JSONDecodeError, TypeError):
                logger.error(f"load_test_data_source(): input file '{source}': Invalid JSON")

    if test_data is not None:

        if 'url' in metadata and 'url' in test_data:
            # Registry metadata 'url' value may now
            # override the corresponding test_data value
            test_data.pop('url')

        # append/override test data to metadata
        metadata.update(test_data)

        metadata['location'] = source

        # the api_name extracted from a URL path
        api_name: str = source.split('/')[-1]
        # remove the trailing file extension
        metadata['api_name'] = api_name.replace(".json", "")

    return metadata


# Key is a resource identifier a.k.a. 'api_name'
# Value is associated Translator SmartAPI Registry metadata dictionary
component_catalog: Dict[str, Dict[str, Any]] = dict()


@deprecated
def cache_resource_metadata(metadata: Dict[str, Any]):
    component = metadata['component']
    assert component in ["KP", "ARA"]
    resource_id: str = metadata['api_name']
    component_catalog[resource_id] = metadata


@deprecated
def get_metadata_by_resource(resource_id: str) -> Optional[Dict[str, Any]]:
    if resource_id in component_catalog:
        metadata: Dict = component_catalog[resource_id]
        return metadata
    else:
        return None


@deprecated
def get_component_by_resource(resource_id: str) -> Optional[str]:
    metadata: Dict = get_metadata_by_resource(resource_id)
    if metadata and "component" in metadata:
        return metadata['component']
    else:
        return None


kp_edges_catalog: Dict[str, Dict[str,  Union[int, str]]] = dict()


@deprecated
def add_kp_edge(resource_id: str, edge_idx: int, edge: Dict[str, Any]):
    metadata: Dict = get_metadata_by_resource(resource_id)
    assert metadata
    if "edges" not in metadata:
        metadata['edges'] = list()
    while len(metadata['edges']) <= edge_idx:
        metadata['edges'].append(None)
    metadata['edges'][edge_idx] = edge


@deprecated
def get_kp_edge(resource_id: str, edge_idx: int) -> Optional[Dict[str, Any]]:
    metadata: Dict = get_metadata_by_resource(resource_id)
    if metadata:
        edges = metadata['edges']
        if 0 <= edge_idx < len(edges):
            return edges[edge_idx]
        logger.warning(f"get_kp_edge(resource_id: {resource_id}, edge_idx: {edge_idx}) out-of-bounds 'edge_idx'?")
    else:
        logger.warning(f"get_kp_edge(resource_id: {resource_id}, edge_idx: {edge_idx}) 'metadata' unavailable?")
    return None


def generate_trapi_kp_tests(metafunc, trapi_version: str, biolink_version: str) -> List:
    """
    Generate set of TRAPI Knowledge Provider unit tests with test data edges.

    :param metafunc: Dict, diverse One Step Pytest metadata
    :param trapi_version, str, TRAPI release set to be used in the validation
    :param biolink_version, str, Biolink Model release set to be used in the validation
    """
    edges: List = []
    idlist: List = []

    # TODO: test_run_id is currently unused in this method; it is otherwise an
    #       optional user session identifier for the test (can be an empty string)
    # test_run_id = metafunc.config.getoption('test_run_id')

    triple_source = metafunc.config.getoption('triple_source')

    kp_metadata: Dict[str, Dict[str, Optional[str]]] = \
        get_test_data_sources(
            source=triple_source,
            trapi_version=trapi_version,
            biolink_version=biolink_version,
            component_type="KP"
        )

    for source, metadata in kp_metadata.items():

        # User CLI may trapi_version, biolink_version may (but not necessarily) here
        # override the target Biolink Model version during KP test data preparation
        kpjson = load_test_data_source(source, metadata)

        if not kpjson:
            # valid test data file not found?
            logger.error(
                f"generate_trapi_kp_tests():  JSON file at test data location '{source}' is missing or invalid"
            )
            continue

        # No point in caching for latest implementation of reporting
        # cache_resource_metadata(kpjson)

        dataset_level_test_exclusions: Set = set()
        if "exclude_tests" in kpjson:
            dataset_level_test_exclusions.update(
                [test for test in kpjson["exclude_tests"] if test in get_unit_test_codes()]
            )

        if not ('url' in kpjson and kpjson['url'].startswith("http")):
            err_msg = f"generate_trapi_kp_tests(): source '{source}' url "
            err_msg += f"{str(kpjson['url'])} is invalid" if 'url' in kpjson else "field is missing or is not a URI"
            err_msg += "... Skipping test data source?"
            logger.error(err_msg)
            continue

        # TODO: see below about echoing the edge input data to the Pytest stdout
        print(f"### Start of Test Input Edges for KP '{kpjson['api_name']}' ###")

        for edge_i, edge in enumerate(kpjson['edges']):

            # We tag each edge internally with its
            # sequence number, for later convenience
            edge['idx'] = edge_i

            # We can already do some basic Biolink Model validation here of the
            # S-P-O contents of the edge being input from the current triples file?
            biolink_validator: BiolinkValidator = \
                check_biolink_model_compliance_of_input_edge(
                    edge,
                    biolink_version=kpjson['biolink_version']
                )
            if biolink_validator.has_messages():
                # defer reporting of errors to higher level of test harness
                edge['pre-validation'] = biolink_validator.get_messages()

            edge['kp_test_data_location'] = kpjson['location']

            edge['url'] = kpjson['url']

            edge['kp_api_name'] = kpjson['api_name']

            edge['trapi_version'] = kpjson['trapi_version']
            edge['biolink_version'] = kpjson['biolink_version']

            if 'infores' in kpjson:
                edge['kp_source'] = f"infores:{kpjson['infores']}"
            else:
                logger.warning(
                    f"generate_trapi_kp_tests(): input file '{source}' "
                    "is missing its 'infores' field value? Inferred from its API name?"
                )
                # create a pseudo-infores from a lower cased and hyphenated API name
                kp_api_name: str = edge['kp_api_name']
                if not kp_api_name:
                    logger.warning("generate_trapi_kp_tests(): KP API Name is missing? Skipping entry...")
                    continue
                kp_infores_object_id = kp_api_name.lower().replace("_", "-")
                edge['kp_source'] = f"infores:{kp_infores_object_id}"

            if 'source_type' in kpjson:
                edge['kp_source_type'] = kpjson['source_type']
            else:
                # If not specified, we assume that the KP is a "primary_knowledge_source"
                edge['kp_source_type'] = "primary"

            if 'query_opts' in kpjson:
                edge['query_opts'] = kpjson['query_opts']
            else:
                edge['query_opts'] = {}

            if dataset_level_test_exclusions:
                if 'exclude_tests' not in edge:
                    edge['exclude_tests']: Set = dataset_level_test_exclusions
                else:
                    # converting List internally to a set
                    edge['exclude_tests'] = set(edge['exclude_tests'])
                    edge['exclude_tests'].update(dataset_level_test_exclusions)

            # convert back to List for JSON serialization safety later
            if 'exclude_tests' in edge:
                edge['exclude_tests'] = list(edge['exclude_tests'])

            edges.append(edge)

            # Start using the object_id of the Infores
            # CURIE of the KP instead of its api_name...
            # resource_id = edge['kp_api_name']
            kp_id = edge['kp_source'].replace("infores:", "")

            #
            # TODO: caching the edge here doesn't help parsing of the results into a report since
            #       the cache is not shared with the parent process.
            #       Instead, we will try to echo the edge directly to stdout, for later parsing for the report.
            #
            # add_kp_edge(resource_id, edge_i, edge)
            # json.dump(edge, stdout)

            edge_id = generate_edge_id(kp_id, edge_i)
            idlist.append(edge_id)

            if metafunc.config.getoption('one', default=False):
                break

            # Circuit breaker for overly large edge test data sets
            if edge_i > REASONABLE_NUMBER_OF_TEST_EDGES:
                break

        print(f"### End of Test Input Edges for KP '{kpjson['api_name']}' ###")

    if "kp_trapi_case" in metafunc.fixturenames:

        metafunc.parametrize('kp_trapi_case', edges, ids=idlist)

        teststyle = metafunc.config.getoption('teststyle')

        # Runtime specified (CLI) constraints on test scope,
        # which will be overridden by file set and specific
        # test triple-level exclude_tests scoping, as captured above
        if teststyle == 'all':
            global_test_inclusions = [
                    oh_util.by_subject,
                    oh_util.inverse_by_new_subject,
                    oh_util.by_object,
                    oh_util.raise_subject_entity,
                    oh_util.raise_object_by_subject,
                    oh_util.raise_predicate_by_subject
            ]
        else:
            global_test_inclusions = [getattr(oh_util, teststyle)]

        metafunc.parametrize("trapi_creator", global_test_inclusions)

    return edges


# Once the smartapi tests are up, we'll want to pass them in here as well
def generate_trapi_ara_tests(metafunc, kp_edges, trapi_version, biolink_version):
    """
    Generate set of TRAPI Autonomous Relay Agents (ARA) unit tests with KP test data edges.

    :param metafunc: Dict, diverse One Step Pytest metadata
    :param kp_edges: List, list of knowledge provider test edges from knowledge providers associated
    :param trapi_version, str, TRAPI release set to be used in the validation
    :param biolink_version, str, Biolink Model release set to be used in the validation
    """
    kp_dict = defaultdict(list)
    for e in kp_edges:
        # We connect ARA's to their KPs by infores (== kp_source) now...
        kp_dict[e['kp_source']].append(e)

    ara_edges = []
    idlist = []

    ara_source = metafunc.config.getoption('ARA_source')

    ara_metadata: Dict[str, Dict[str, Optional[str]]] = \
        get_test_data_sources(
            source=ara_source,
            trapi_version=trapi_version,
            biolink_version=biolink_version,
            component_type="ARA"
        )

    for source, metadata in ara_metadata.items():

        # User CLI may override here the target Biolink Model version during KP test data preparation
        arajson = load_test_data_source(source, metadata)

        if not arajson:
            # valid test data file not found?
            logger.error(
                f"generate_trapi_ara_tests(): JSON file at test data location '{source}' is missing or invalid"
            )
            continue

        # No point in caching for latest implementation of reporting
        # cache_resource_metadata(arajson)

        for kp in arajson['KPs']:

            #
            # TODO: use of KP infores ('kp_source') CURIES in the Registry ARA spec
            #       likely now completely breaks the old filename-centric
            #       (non-Registry) local test_triples mechanism for KP resolution
            # # By replacing spaces in name with underscores,
            # # should give get the KP "api_name" indexing the edges.
            # kp = '_'.join(kp.split())

            if kp not in kp_dict:
                logger.warning(
                    f"generate_trapi_ara_tests(): '{kp}' test edges not (yet) available for ARA {source}. Skipping..."
                )
                continue

            for edge_i, kp_edge in enumerate(kp_dict[kp]):

                edge: dict = kp_edge.copy()

                edge['url'] = arajson['url']
                edge['ara_test_data_location'] = arajson['location']

                edge['ara_api_name'] = arajson['api_name']

                # We override the KP TRAPI and Biolink Model versions with the ARA values here!

                edge['trapi_version'] = arajson['trapi_version']
                edge['biolink_version'] = arajson['biolink_version']

                # Resetting the Biolink Model version here may have the peculiar side effect of some
                # KP edge test data now becoming non-compliant with the 'new' ARA Biolink Model version?
                biolink_validator: BiolinkValidator = \
                    check_biolink_model_compliance_of_input_edge(
                        edge,
                        biolink_version=arajson['biolink_version']
                    )
                if biolink_validator.has_messages():
                    # defer reporting of errors to higher level of test harness
                    edge['pre-validation'] = biolink_validator.get_messages()

                if 'infores' in arajson:
                    edge['ara_source'] = f"infores:{arajson['infores']}"
                else:
                    logger.warning(
                        f"generate_trapi_ara_tests(): input file '{source}' " +
                        "is missing its ARA 'infores' field.  We infer one from "
                        "the ARA 'api_name', but edge provenance may not be properly tested?"
                    )
                    # create a pseudo-infores from a lower cased and hyphenated API name
                    ara_api_name: str = edge['ara_api_name']
                    if not ara_api_name:
                        logger.warning("generate_trapi_ara_tests(): ARA API Name is missing? Skipping entry...")
                        continue
                    ara_infores_object_id = ara_api_name.lower().replace("_", "-")
                    edge['ara_source'] = f"infores:{ara_infores_object_id}"

                if 'kp_source' in kp_edge:
                    edge['kp_source'] = kp_edge['kp_source']
                else:
                    logger.warning(
                        f"generate_trapi_ara_tests(): KP '{kp}' edge is missing its 'kp_source' infores." +
                        "Inferred from KP name, but KP provenance may not be properly tested?"
                    )
                    edge['kp_source'] = f"infores:{kp}"
                edge['kp_source_type'] = kp_edge['kp_source_type']

                if 'query_opts' in arajson:
                    edge['query_opts'] = arajson['query_opts']
                else:
                    edge['query_opts'] = {}

                # Start using the object_id of the Infores CURIEs of the ARA's and KP's, instead of their api_names...
                # resource_id = f"{edge['ara_api_name']}|{edge['kp_api_name']}"
                ara_id = edge['ara_source'].replace("infores:", "")
                kp_id = edge['kp_source'].replace("infores:", "")
                resource_id = f"{ara_id}|{kp_id}"

                edge_id = generate_edge_id(resource_id, edge_i)
                idlist.append(edge_id)

                ara_edges.append(edge)

    metafunc.parametrize('ara_trapi_case', ara_edges, ids=idlist)


def pytest_generate_tests(metafunc):
    """This hook is run at test generation time.  These functions look at the configured triples on disk
    and use them to parameterize inputs to the test functions. Note that this gets called multiple times, once
    for each test_* function, and you can only parameterize an argument to that specific test_* function.
    However, for the ARA tests, we still need to get the KP data, since that is where the triples live."""

    # KP/ARA TRAPI version may be overridden
    # on the command line; maybe 'None' => no override
    trapi_version = metafunc.config.getoption('TRAPI_Version')
    logger.debug(f"pytest_generate_tests(): caller specified TRAPI_Version == {str(trapi_version)}")

    # KP/ARA Biolink Model version may be overridden
    # on the command line; maybe 'None' => no override
    biolink_version = metafunc.config.getoption('Biolink_Version')
    logger.debug(f"pytest_generate_tests(): caller specified Biolink_Version == {str(biolink_version)}")

    trapi_kp_edges = generate_trapi_kp_tests(
        metafunc,
        trapi_version=trapi_version,
        biolink_version=biolink_version
    )

    if metafunc.definition.name == 'test_trapi_aras':
        generate_trapi_ara_tests(
            metafunc,
            trapi_kp_edges,
            trapi_version=trapi_version,
            biolink_version=biolink_version
        )
