"""
Configure one hop tests
"""
from typing import Optional, Union, List, Set, Dict, Any, Tuple
from collections import defaultdict

import logging

from pytest_harvest import get_session_results_dct

from reasoner_validator.biolink import check_biolink_model_compliance_of_input_edge, BiolinkValidator
from reasoner_validator.versioning import latest

from translator.registry import (
    get_remote_test_data_file,
    get_the_registry_data,
    extract_component_test_metadata_from_registry
)

from translator.trapi import generate_edge_id, UnitTestReport

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


def _new_kp_resource_summary(
        url: str,
        x_maturity: str,
        trapi_version: str,
        biolink_version: str
) -> Dict[str, Union[str, Dict]]:
    """
    Initialize a dictionary to capture statistics for a single KP test case summary.

    :param url: str, KP or ARA component endpoint being tested
    :param x_maturity: str, x-maturity environment within which the tested url is hosted
    :param trapi_version: str, TRAPI version associated with the test case (SemVer)
    :param biolink_version:  str, Biolink Model version associated with the test case (SemVer)

    :return: Dict[str, Union[int, str, Dict]], initialized
    """
    kp_resource_summary: Dict[str, Union[str, Dict]] = {
        'url': url,
        'x_maturity': x_maturity,
        'trapi_version': trapi_version,
        'biolink_version': biolink_version,
        'test_edges': dict()
    }
    return kp_resource_summary


def _new_kp_recommendation_summary(
        url: str,
        x_maturity: str,
        trapi_version: str,
        biolink_version: str
) -> Dict[str, Union[str, Dict]]:
    """
    Initialize a dictionary to capture recommendations for a single KP test case summary.

    :param url: str, KP or ARA component endpoint being tested
    :param x_maturity: str, x-maturity environment within which the tested url is hosted
    :param trapi_version: str, TRAPI version associated with the test case (SemVer)
    :param biolink_version:  str, Biolink Model version associated with the test case (SemVer)

    :return: Dict[str, Union[int, str, Dict]], initialized
    """
    new_recommendations: Dict[str, Union[str, Dict]] = {
        'url': url,
        'x_maturity': x_maturity,
        'trapi_version': trapi_version,
        'biolink_version': biolink_version,
        'errors': dict(),
        'warnings': dict(),
        'information': dict()
    }
    return new_recommendations


def _compile_recommendations(
        recommendation_summary: Dict[str, Union[str, Dict]],
        test_report: UnitTestReport,
        test_case,
        test_id: str
):
    #     "errors": {
    #       "error.edge.predicate.unknown": [
    #         {
    #           "message": {
    #             "context": "Query Graph",
    #             "edge_id": "a--['biolink:has_active_component']->b",
    #             "predicate": "biolink:has_active_component",
    #             "code": "error.edge.predicate.unknown"
    #           },
    #           "test_data": {
    #             "subject_category": "biolink:Gene",
    #             "object_category": "biolink:CellularComponent",
    #             "predicate": "biolink:active_in",
    #             "subject": "ZFIN:ZDB-GENE-060825-345",
    #             "object": "GO:0042645"
    #           },
    #           "test": "inverse_by_new_subject"
    #         }
    #       ],
    # ...
    #    }
    # TODO: what if test_case lacks some of the keys?
    test_data: Dict = {
        "subject_category": test_case["subject_category"],
        "object_category": test_case["object_category"],
        "predicate": test_case["predicate"],
        "subject": test_case["subject"],
        "object": test_case["object"]
    }

    # Validation messages are list of dictionary objects with
    # one 'code' key and optional (variable key) parameters
    # Leveraging function closure here...
    def _capture_messages(message_type: str, messages: List):
        for entry in messages:
            code: str = entry.pop('code')
            if code not in recommendation_summary[message_type]:
                recommendation_summary[message_type][code] = list()
            item: Dict = {
                "message": entry,
                "test_data": test_data,
                "test": test_id
            }
            recommendation_summary[message_type][code].append(item)

    if test_report.has_errors():
        _capture_messages(message_type="errors", messages=test_report.get_errors())

    if test_report.has_warnings():
        _capture_messages(message_type="warnings", messages=test_report.get_warnings())

    if test_report.has_information():
        _capture_messages(message_type="information", messages=test_report.get_info())


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
# 5. Recommendations: KP (or ARA/KP) non-redundant hierarchical summary of validation messages
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
    recommendation_summaries: Dict = dict()
    case_details: Dict = dict()

    for unit_test_key, details in session_results.items():

        rb: Dict = details['fixtures']['results_bag']

        # sanity check: clean up MS Windoze EOL characters, when present in results_bag keys
        rb = {key.strip("\r\n"): value for key, value in rb.items()}

        # Sanity check? Missing 'case' would
        # seem like an SRI Testing logical bug?
        assert 'case' in rb
        test_case = rb['case']

        # clean up the name for safe file system usage
        component, ara_id, kp_id, edge_num, test_id, edge_details_key = parse_unit_test_name(
            unit_test_key=unit_test_key
        )

        # Sanity check: missing 'url' or 'x_maturity is likely a logical bug in SRI Testing?
        assert 'url' in test_case
        url: str = test_case['url']

        assert 'x_maturity' in test_case
        x_maturity: str = test_case['x_maturity']

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

            # Set up indexed resource summaries ...
            resource_summaries[component] = dict()

            # ... and recommendation summaries in parallel
            recommendation_summaries[component] = dict()

        case_summary: Dict
        if ara_id:
            if ara_id not in test_run_summary[component]:
                test_run_summary[component][ara_id] = dict()
                test_run_summary[component][ara_id]['url'] = url
                test_run_summary[component][ara_id]['x_maturity'] = x_maturity
                test_run_summary[component][ara_id]['test_data_location'] = test_case['ara_test_config_location']
                test_run_summary[component][ara_id]['kps'] = dict()

                resource_summaries[component][ara_id] = dict()
                recommendation_summaries[component][ara_id] = dict()

            if kp_id not in test_run_summary[component][ara_id]['kps']:
                test_run_summary[component][ara_id]['kps'][kp_id] = _new_kp_test_case_summary(
                    trapi_version=trapi_version,
                    biolink_version=biolink_version
                )
                resource_summaries[component][ara_id][kp_id] = _new_kp_resource_summary(
                    url=url,
                    x_maturity=x_maturity,
                    trapi_version=trapi_version,
                    biolink_version=biolink_version
                )
                recommendation_summaries[component][ara_id][kp_id] = _new_kp_recommendation_summary(
                    url=url,
                    x_maturity=x_maturity,
                    trapi_version=trapi_version,
                    biolink_version=biolink_version
                )

            case_summary = test_run_summary[component][ara_id]['kps'][kp_id]
            resource_summary = resource_summaries[component][ara_id][kp_id]
            recommendation_summary = recommendation_summaries[component][ara_id][kp_id]

        else:
            if kp_id not in test_run_summary[component]:
                test_run_summary[component][kp_id] = _new_kp_test_case_summary(
                    trapi_version=trapi_version,
                    biolink_version=biolink_version
                )
                test_run_summary[component][kp_id]['url'] = url
                test_run_summary[component][kp_id]['x_maturity'] = x_maturity
                test_run_summary[component][kp_id]['test_data_location'] = test_case['ks_test_data_location']

                resource_summaries[component][kp_id] = _new_kp_resource_summary(
                    url=url,
                    x_maturity=x_maturity,
                    trapi_version=trapi_version,
                    biolink_version=biolink_version
                )
                recommendation_summaries[component][kp_id] = _new_kp_recommendation_summary(
                    url=url,
                    x_maturity=x_maturity,
                    trapi_version=trapi_version,
                    biolink_version=biolink_version
                )

            case_summary = test_run_summary[component][kp_id]
            resource_summary = resource_summaries[component][kp_id]
            recommendation_summary = recommendation_summaries[component][kp_id]

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
        if test_report and test_report.has_messages():
            resource_summary['test_edges'][idx]['results'][test_id]['validation'] = test_report.get_messages()

            # Capture recommendations
            _compile_recommendations(recommendation_summary, test_report, test_case, test_id)

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

        # Capture more request details for tests that are run (not skipped)
        if details['status'] != 'skipped':

            if 'request' in rb:
                # TODO: maybe the 'request' document could be persisted
                #       separately JIT, to avoid using too much RAM?
                test_details['request'] = rb['request']
            else:
                test_details['request'] = "No 'request' generated for this unit test?"

        # Capture more response details for test failures
        if details['status'] == 'failed':
            if 'response' in rb:
                case_response: Dict = dict()
                case_response['url'] = test_case['url'] if 'url' in test_case else "Unknown?!"
                case_response['x_maturity'] = test_case['x_maturity'] if 'x_maturity' in test_case else "Unknown?!"
                case_response['unit_test_key'] = unit_test_key
                case_response['http_status_code'] = rb["response"]["status_code"]
                case_response['response'] = rb['response']['response_json']

                response_document_key = f"{edge_details_key}-{test_id}"
                test_run.save_json_document(
                    document_type="TRAPI I/O",
                    document=case_response,
                    document_key=response_document_key,
                    index=[],
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
            document_key=edge_details_key,
            index=[]
        )

    # TODO: could the following resource test summaries and recommendations code be refactored to be more DRY?
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
                document_key=document_key,
                index=[]
            )

    # All KP's called by ARA's
    if "ARA" in resource_summaries:
        ara_summaries = resource_summaries["ARA"]
        for ara in ara_summaries:
            for kp in ara_summaries[ara]:
                # Save Test Run embedded KP Resource Summary
                document_key: str = f"ARA/{ara}/{kp}/resource_summary"
                test_run.save_json_document(
                    document_type="ARA Embedded KP Summary",
                    document=ara_summaries[ara][kp],
                    document_key=document_key,
                    index=[]
                )
    #
    # Save the various recommendation summaries
    #
    # All KP's individually
    if "KP" in recommendation_summaries:
        kp_summaries = recommendation_summaries["KP"]
        for kp in kp_summaries:
            # Save Test Run Recommendations
            document_key: str = f"KP/{kp}/recommendations"
            test_run.save_json_document(
                document_type="Direct KP Recommendations",
                document=kp_summaries[kp],
                document_key=document_key,
                index=[]
            )

    # All KP's called by ARA's
    if "ARA" in recommendation_summaries:
        ara_summaries = recommendation_summaries["ARA"]
        for ara in ara_summaries:
            for kp in ara_summaries[ara]:
                # Save Test Run embedded KP Resource Recommendations
                document_key: str = f"ARA/{ara}/{kp}/recommendations"
                test_run.save_json_document(
                    document_type="ARA Embedded KP Recommendations",
                    document=ara_summaries[ara][kp],
                    document_key=document_key,
                    index=[]
                )

    # Save Test Run Summary
    test_run.save_json_document(
        document_type="Test Run Summary",
        document=test_run_summary,
        document_key="test_run_summary",
        index=[]
    )


def pytest_addoption(parser):
    """
    :param parser:
    """
    #  Mostly used when the SRI Testing harness is run by a web service
    parser.addoption(
        "--test_run_id", action="store", default="",
        help='Optional Test Run Identifier for internal use to index test results.'
    )
    # Override the Translator SmartAPI Registry published
    # 'x-trapi' TRAPI release property value of the target resources.
    parser.addoption(
        "--trapi_version", action="store", default=None,
        help='TRAPI API version to use for validation, overriding' +
             ' Translator SmartAPI Registry property value ' +
             '(Default: latest public release or ).'
    )
    # Override the Translator SmartAPI Registry published
    # 'x-translator' Biolink Model release property value of the target resources.
    parser.addoption(
        "--biolink_version", action="store", default=None,
        help='Biolink Model version to use for validation, overriding' +
             ' Translator SmartAPI Registry property value ' +
             '(Default: latest public release or ).'
    )
    parser.addoption(
        "--kp_id", action="store", default=None,
        help='Knowledge Provider identifier ("KP") targeted for testing (Default: None).'
    )
    parser.addoption(
        "--ara_id", action="store", default=None,
        help='Autonomous Relay Agent ("ARA") targeted for testing (Default: None).'
    )
    parser.addoption(
        "--x_maturity", action="store", default=None,  # 'testing',
        help='Target x_maturity server environment for testing (Default: None).'
    )
    parser.addoption("--teststyle", action="store", default='all', help='Which Test to Run?')
    parser.addoption("--one", action="store_true", help="Only use first edge from each KP file")
    

def _fix_path(file_path: str) -> str:
    """
    Fixes OS specific path string issues (especially, for MS Windows)
    
    :param file_path: file path to be repaired
    """
    file_path = file_path.replace("\\", "/")
    return file_path


def get_test_data_sources(
        component_type: str,
        source: Optional[str] = None,
        x_maturity: Optional[str] = None,
        trapi_version: Optional[str] = None,
        biolink_version: Optional[str] = None
) -> Dict[str, Dict[str, Optional[Union[str, Dict]]]]:
    """
    Retrieves a dictionary of metadata of 'component_type', indexed by 'source' identifier.

    :param source: Optional[str], 'ara_id' or 'kp_id' source of test configuration data in the registry.
                                  Take 'all' of the given component type if the source is None

    :param x_maturity: Optional[str], x_maturity environment target for test run (system chooses if not specified)
    :param component_type: str, component type 'KP' or 'ARA'
    :param trapi_version: SemVer caller override of TRAPI release target for validation (Default: None)
    :param biolink_version: SemVer caller override of Biolink Model release target for validation (Default: None)

    :return: Dict[str, Dict[str, Optional[Union[str, Dict]]]], service metadata dictionary
    """
    # Access service metadata from the Translator SmartAPI Registry,
    # indexed using the "test_data_location" field as the unique key
    registry_data: Dict = get_the_registry_data()
    service_metadata = extract_component_test_metadata_from_registry(registry_data, component_type, source, x_maturity)

    # Possible CLI override of the metadata value of
    # TRAPI and/or Biolink Model releases used for data validation
    if trapi_version:
        for service_name in service_metadata.keys():
            service_metadata[service_name]['trapi_version'] = latest.get(trapi_version)

    if biolink_version:
        for service_name in service_metadata.keys():
            service_metadata[service_name]['biolink_version'] = biolink_version

    return service_metadata


def load_test_data_sources(
        registry_metadata: Dict[str, Any],
        source_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Load JSON metadata file(s) from a specified component test data source. Note that with the latest
    Translator SmartAPI Registry data model for info.x-trapi.test_data_location properties, that the
    actual data loaded may relate to several distinct x-maturity environments that may have more than
    one JSON test file sources.

    :param registry_metadata: Dict[str, Any], metadata associated with source
    :param source_id: str, reference id of the infores CURIE of the source component owning the registry metadata
    :return: Optional[Dict[str, Any], annotated KP test edges or ARA configuration metadata; 'None' if unavailable
    """
    # sanity check
    assert registry_metadata is not None
    if 'sources' not in registry_metadata:
        registry_metadata['sources'] = dict()

    test_data_locations: List[str] = registry_metadata['test_data_location']
    for test_data_url in test_data_locations:

        test_data = get_remote_test_data_file(test_data_url)

        if not test_data:
            continue

        if 'infores' not in test_data:
            if source_id:
                test_data['infores'] = source_id  # default 'infores' is from component being tested
            else:
                logger.warning(f"Test data missing 'infores': {str(test_data)[0:20]}...Skipping!")
                continue

        # Registry metadata resource endpoint 'url' values now
        # override any corresponding legacy test_data file value
        if 'url' in registry_metadata and 'url' in test_data:
            test_data.pop('url')

        infores = test_data.pop('infores')
        if infores not in registry_metadata['sources']:
            registry_metadata['sources'][infores] = dict()

        source = registry_metadata['sources'][infores]
        source.update(test_data)
        source['location'] = test_data_url

    return registry_metadata


# Key is a resource identifier a.k.a. 'kp_id' or 'ara_id'
# Value is associated Translator SmartAPI Registry metadata dictionary
component_catalog: Dict[str, Dict[str, Any]] = dict()


kp_edges_catalog: Dict[str, Dict[str,  Union[int, str]]] = dict()


def get_ara_metadata(metafunc, trapi_version, biolink_version) -> Dict[str, Dict[str, Optional[Union[str, Dict]]]]:
    # Here, the ara_id may be None, in which case,
    # 'ara_metadata' returns all available ARA's
    ara_id = metafunc.config.getoption('ara_id')
    x_maturity: Optional[str] = metafunc.config.getoption('x_maturity')

    if x_maturity and x_maturity.lower() not in ["production", "staging", "testing", "development"]:
        x_maturity = None

    if ara_id == "SKIP":
        return dict()  # no ARA's to validate

    # Note: the ARA's trapi_version and biolink_version may be overridden here
    return get_test_data_sources(
            source=ara_id,
            x_maturity=x_maturity,
            trapi_version=trapi_version,
            biolink_version=biolink_version,
            component_type="ARA"
    )


def id_parts(identifier: str) -> Optional[Tuple[str, str, str]]:
    id_part = identifier.split(',')
    if len(id_part) != 3:
        logger.error(f"Source id '{identifier}' is invalid?")
        return None

    ara_id, trapi_version, biolink_version = id_part
    return ara_id, trapi_version, biolink_version


def get_kp_metadata(
        metafunc,
        ara_metadata: Dict,
        trapi_version: str,
        biolink_version: str
) -> Dict[str, Dict[str, Optional[Union[str, Dict]]]]:

    # Here, the kp_id may be None, in which case,
    # 'kp_metadata' returns all available KP's
    target_kp_id = metafunc.config.getoption('kp_id')
    x_maturity: Optional[str] = metafunc.config.getoption('x_maturity')

    if x_maturity and x_maturity.lower() not in ["production", "staging", "testing", "development"]:
        # Sanity check....
        x_maturity = None

    # Note: the KP's trapi_version and biolink_version may be overridden here
    kp_metadata: Dict[str, Dict[str, Optional[str]]] = \
        get_test_data_sources(
            source=target_kp_id,
            x_maturity=x_maturity,
            trapi_version=trapi_version,
            biolink_version=biolink_version,
            component_type="KP"
        )

    if len(ara_metadata) == 1:
        # if we have exactly one ARA, then  we should only pay attention
        # to KPs indicated by test configuration as called by that ARA.
        # Since we don't want to pop the metadata from its dictionary but
        # don't know the ara_id, we need to use a for loop to access it
        for ara_release, metadata in ara_metadata.items():

            ara_id: Optional[str]
            ara_id, trapi_version, biolink_version = id_parts(ara_release)
            arajson: Dict = load_test_data_sources(metadata, source_id=ara_id)
            if not arajson:
                # valid test data file not found?
                logger.error(
                    f"get_kp_metadata(): '{ara_release}' has no valid test_data_location information?")
                continue

            # Blissful assumption here is that our kp_metadata
            # entries will all have infores CURIE references
            kept: Dict = dict()

            # Although in principle, ARA's can have multiple test configuration files, this will
            # likely be rare,  but nonetheless, we need to iterate as if it is the case
            sources = arajson['sources']
            for infores, test_config in sources.items():

                kps: Set[str] = {kp_id for kp_id in test_config['KPs']}

                for kp_source, kp_metadata in kp_metadata.items():
                    if 'infores' in kp_metadata and f"infores:{kp_metadata['infores']}" in kps:
                        kept[kp_source] = kp_metadata

            kp_metadata = kept

    return kp_metadata


def generate_trapi_kp_tests(metafunc, kp_metadata) -> List:
    """
    Generate set of TRAPI Knowledge Provider unit tests with test data edges.

    :param metafunc: Dict, diverse One Step Pytest metadata
    :param kp_metadata, Dict[str, Dict[str, Optional[Union[str, Dict]]]], test edge data for one or more KPs
    """
    edges: List = []
    idlist: List = []

    for kp_release, metadata in kp_metadata.items():

        kp_id: Optional[str]

        kp_id, trapi_version, biolink_version = id_parts(kp_release)

        kpjson: Dict = load_test_data_sources(metadata, source_id=kp_id)

        if not kpjson:
            # valid test data file not found?
            logger.error(
                f"generate_trapi_kp_tests():  JSON file at test data location '{kp_release}' is missing or invalid"
            )
            continue

        if not ('url' in kpjson and kpjson['url'].startswith("http")):
            err_msg = f"generate_trapi_kp_tests(): source '{kp_release}' url "
            err_msg += f"{str(kpjson['url'])} is invalid" if 'url' in kpjson else "field is missing or is not a URI"
            err_msg += "... Skipping test data source?"
            logger.error(err_msg)
            continue

        # TODO: see below about echoing the edge input data to the Pytest stdout
        print(f"### Start of Test Input Edges for KP '{kp_id}' ###")

        sources: Dict = kpjson['sources']
        for infores, test_data in sources.items():

            dataset_level_test_exclusions: Set = set()
            if "exclude_tests" in test_data:
                dataset_level_test_exclusions.update(
                    [test for test in test_data["exclude_tests"] if test in get_unit_test_codes()]
                )

            if 'edges' not in test_data:
                logger.warning(f"Test Data for from '{infores}' has now edges? Weird... skipping!")
                continue

            for edge_i, edge in enumerate(test_data['edges']):

                # We tag each edge internally with its
                # sequence number, for later convenience
                edge['idx'] = edge_i
                edge['kp_id'] = f"infores:{kp_id}"

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

                edge['ks_test_data_location'] = test_data['location']

                edge['url'] = kpjson['url']
                edge['x_maturity'] = kpjson['x_maturity']

                edge['trapi_version'] = kpjson['trapi_version']
                edge['biolink_version'] = kpjson['biolink_version']

                edge['kp_source'] = f"infores:{infores}"

                if 'source_type' in test_data:
                    edge['kp_source_type'] = test_data['source_type']
                else:
                    # If not specified, we assume that the test data target
                    # Knowledge Source is a "primary_knowledge_source"
                    edge['kp_source_type'] = "primary"

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

                edge_id = generate_edge_id(kp_id, edge_i)
                idlist.append(edge_id)

                if metafunc.config.getoption('one', default=False):
                    break

                # Circuit breaker for overly large edge test data sets
                if edge_i > REASONABLE_NUMBER_OF_TEST_EDGES:
                    break

        print(f"### End of Test Input Edges for KP '{kp_id}' ###")

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
def generate_trapi_ara_tests(metafunc, kp_edges, ara_metadata):
    """
    Generate set of TRAPI Autonomous Relay Agents (ARA) unit tests with KP test data edges.

    :param metafunc: Dict, diverse One Step Pytest metadata
    :param kp_edges: List, list of knowledge provider test edges from knowledge providers associated
    :param ara_metadata, Dict[str, Dict[str, Optional[str]]], test run configuration for one or more ARAs
    """
    kp_dict = defaultdict(list)
    for e in kp_edges:
        # We connect ARA's to their KPs by infores (== kp_source) now...
        kp_dict[e['kp_source']].append(e)

    ara_edges = []
    idlist = []

    for ara_release, metadata in ara_metadata.items():

        ara_id: Optional[str]
        ara_id, trapi_version, biolink_version = id_parts(ara_release)
        arajson: Dict = load_test_data_sources(metadata, source_id=ara_id)
        if not arajson:
            # valid test data file not found?
            logger.error(f"generate_trapi_ara_tests(): '{ara_release}' has no valid test_data_location information?")
            continue

        # Although in principle, ARA's can have multiple test configuration files, this will
        # likely be rare,  but nonetheless, we need to iterate as if it is the case
        sources = arajson['sources']
        for infores, test_config in sources.items():

            for kp in test_config['KPs']:

                if kp not in kp_dict:
                    logger.warning(
                        f"generate_trapi_ara_tests(): '{kp}' test edges not (yet)" +
                        f" available for this source '{infores}' in ARA {ara_release}. Skipping..."
                    )
                    continue

                for edge_i, kp_edge in enumerate(kp_dict[kp]):

                    edge: dict = kp_edge.copy()

                    edge['ara_id'] = f"infores:{ara_id}"

                    edge['url'] = arajson['url']
                    edge['x_maturity'] = arajson['x_maturity']
                    edge['ara_test_config_location'] = test_config['location']

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

                    edge['ara_source'] = f"infores:{infores}"

                    if 'kp_source' in kp_edge:
                        edge['kp_source'] = kp_edge['kp_source']
                    else:
                        logger.warning(
                            f"generate_trapi_ara_tests(): KP '{kp}' edge is missing its 'kp_source' infores." +
                            "Inferred from KP name, but KP provenance may not be properly tested?"
                        )
                        edge['kp_source'] = kp

                    edge['kp_source_type'] = kp_edge['kp_source_type']

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
    trapi_version = metafunc.config.getoption('trapi_version')
    logger.debug(f"pytest_generate_tests(): caller specified trapi_version == {str(trapi_version)}")

    # KP/ARA Biolink Model version may be overridden
    # on the command line; maybe 'None' => no override
    biolink_version = metafunc.config.getoption('biolink_version')
    logger.debug(f"pytest_generate_tests(): caller specified biolink_version == {str(biolink_version)}")

    # Note: the ARA and KP trapi_version and biolink_version values
    #       may be overridden here by the CLI caller values
    ara_metadata = get_ara_metadata(metafunc, trapi_version, biolink_version)
    kp_metadata = get_kp_metadata(metafunc, ara_metadata, trapi_version, biolink_version)

    trapi_kp_edges = generate_trapi_kp_tests(metafunc, kp_metadata)

    if metafunc.definition.name == 'test_trapi_aras':
        generate_trapi_ara_tests(metafunc, trapi_kp_edges, ara_metadata)
