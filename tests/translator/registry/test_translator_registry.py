"""
Unit tests for Translator SmartAPI Registry
"""
from typing import Optional, Union, Tuple, Dict, List
import logging
import pytest

from sri_testing.translator.registry import (
    get_default_url,
    rewrite_github_url,
    query_smart_api,
    SMARTAPI_QUERY_PARAMETERS,
    tag_value,
    get_the_registry_data,
    extract_component_test_metadata_from_registry,
    get_testable_resources_from_registry,
    get_testable_resource,
    source_of_interest,
    validate_testable_resource,
    live_trapi_endpoint,
    select_endpoint
)

logger = logging.getLogger(__name__)

# Current default major.minor TRAPI SemVer version"
DEF_M_M_TRAPI = "1.4"

# Current default major.minor.patch TRAPI SemVer version"
DEF_M_M_P_TRAPI = "1.4.0"

TEST_KP_BASEURL = "https://translator.broadinstitute.org/molepro/trapi/v"
KP_TEST_DATA_URL = "https://github.com/broadinstitute/molecular-data-provider/blob/" +\
                   "master/test/data/MolePro-test-data.json"

TEST_ARA_BASEURL = "https://arax.ncats.io/api/arax/v"
ARA_TEST_DATA_URL = ""


def test_get_testable_resources_from_registry():
    registry_data: Optional[Dict] = get_the_registry_data()

    assert registry_data, "Registry inaccessible?"

    resources: Tuple[Dict[str, List[str]], Dict[str, List[str]]] = \
        get_testable_resources_from_registry(registry_data)

    assert len(resources) > 0, "No testable resources in the Registry?"
    assert len(resources[0]) > 0, "No testable resources in the Registry?"
    assert "sri-reference-kg" in resources[0]
    assert len(resources[1]) > 0, "No testable resources in the Registry?"
    assert "arax" in resources[1]


@pytest.mark.parametrize(
    "query",
    [
        (None, None),
        ("", None),
        (list(), None),
        (dict(), None),
        ("http://test_data", "http://test_data"),
        (
            "https://github.com/broadinstitute/molecular-data-provider/blob" +
            "/master/test/data/MolePro-test-data.json",
            "https://raw.githubusercontent.com/broadinstitute/molecular-data-provider" +
            "/master/test/data/MolePro-test-data.json"
        ),
        (
            [
                "http://first_test_data",
                "http://second_test_data"
            ],
            "http://first_test_data"
        ),
        (
            {
                'default': "https://github.com/broadinstitute/molecular-data-provider" +
                           "/blob/master/test/data/MolePro-test-data.json",
                'production': "http://production_test_data",
                'staging': "http://staging_test_data",
                'testing': "http://testing_test_data",
                'development': "http://development_test_data",
            },
            "https://raw.githubusercontent.com/broadinstitute/molecular-data-provider" +
            "/master/test/data/MolePro-test-data.json"
        ),
        (
            {
                'default': "http://default_test_data",
                'production': "http://production_test_data",
                'staging': "http://staging_test_data",
                'testing': "http://testing_test_data",
                'development': "http://development_test_data",
            },
            "http://default_test_data"
        ),
        (
            {
                'testing': "http://testing_test_data",
                'development': "http://development_test_data",
                'production': "http://production_test_data",
                'staging': "http://staging_test_data"
            },
            "http://production_test_data"
        ),
        (
            {
                'our_testing': "http://testing_test_data",
                'development': "http://development_test_data",
                'the_production': "http://production_test_data",
                'staging': "http://staging_test_data"
            },
            "http://staging_test_data"
        )
    ]
)
def test_get_default_url(query: Tuple[Optional[Union[str, List, Dict]], str]):
    # get_default_url(test_data_location: Optional[Union[str, List, Dict]]) -> Optional[str]
    assert get_default_url(query[0]) == query[1]


@pytest.mark.parametrize(
    "url,outcome",
    [
        ("", False),
        ("https://foobar.com", False),

        # This particular endpoint is valid and online as of 15 May 2023
        # but may need to be revised in the future, as Translator resources evolve?
        (f"{TEST_KP_BASEURL}{DEF_M_M_TRAPI}", True)
    ]
)
def test_live_trapi_endpoint(url: str, outcome: bool):
    data: Optional[Dict] = live_trapi_endpoint(url)
    assert (data is not None) is outcome


# def select_endpoint(
#         server_urls: Dict[str, List],
#         test_data_location: Optional[Union[str, List, Dict]]
# ) -> Optional[Tuple[str, str]]
@pytest.mark.parametrize(
    "query",
    [
        (dict(), "", None),  # Query 0: empty parameters - variant 1
        (dict(), list(), None),  # Query 1: empty parameters - variant 2
        (dict(), dict(), None),  # Query 2: empty parameters - variant 3
        (   # Query 3 - complete server_urls for all x-maturity; simple string URL text_data_location
            {
                'testing': ["http://testing_endpoint"],
                'development': ["http://development_endpoint"],
                'production': ["http://production_endpoint"],
                'staging': ["http://staging_endpoint"]
            },
            "http://test_data",
            (
                "http://production_endpoint",
                "production",
                "http://test_data"
            )
        ),
        (   # Query 4 - complete server_urls for all x-maturity; direct list of string URLs text_data_location
            {
                'testing': ["http://testing_endpoint"],
                'development': ["http://development_endpoint"],
                'production': ["http://production_endpoint"],
                'staging': ["http://staging_endpoint"]
            },
            [
                "http://test_data_1",
                "http://test_data_2",
            ],
            (
                "http://production_endpoint",
                "production",
                [
                    "http://test_data_1",
                    "http://test_data_2",
                ]
            )
        ),
        (   # Query 5 - complete server_urls for all x-maturity; full JSON object text_data_location without 'default'
            {
                'testing': ["http://testing_endpoint"],
                'development': ["http://development_endpoint"],
                'production': ["http://production_endpoint"],
                'staging': ["http://staging_endpoint"]
            },
            {
                'testing': "http://testing_test_data",
                'development': "http://development_test_data",
                'production': "http://production_test_data",
                'staging': "http://staging_test_data"
            },
            (
                "http://production_endpoint",
                "production",
                "http://production_test_data"
            )
        ),
        (   # Query 6 - complete server_urls for all x-maturity; JSON object text_data_location with just 'default'
            {
                'testing': ["http://testing_endpoint"],
                'development': ["http://development_endpoint"],
                'production': ["http://production_endpoint"],
                'staging': ["http://staging_endpoint"]
            },
            {
                'default': "http://default_test_data"
            },
            (
                "http://production_endpoint",
                "production",
                "http://default_test_data"
            )
        ),
        (   # Query 7 - partial server_urls for x-maturity; JSON object text_data_location with just 'default'
            {
                'testing': ["http://testing_endpoint"],
                'staging': ["http://staging_endpoint"]
            },
            {
                'default': "http://default_test_data"
            },
            (
                "http://staging_endpoint",
                "staging",
                "http://default_test_data"
            )
        ),
        (   # Query 8 - partial server_urls for x-maturity; non-overlapping object text_data_location without 'default'
            {
                'testing': ["http://testing_endpoint"],
                'production': ["http://production_endpoint"],
                'staging': ["http://staging_endpoint"]
            },
            {
                'development': "http://development_test_data"
            },
            None
        ),
        (   # Query 9 - partial server_urls for x-maturity; non-overlapping object text_data_location with 'default'
            {
                'testing': ["http://testing_endpoint"],
                'staging': ["http://staging_endpoint"]
            },
            {
                'default': "http://default_test_data",
                'development': "http://development_test_data"
            },
            (
                "http://staging_endpoint",
                "staging",
                "http://default_test_data"
            )
        ),
        (   # Query 10 - full server_urls for x-maturity; JSON object text_data_location with only one x-maturity
            {
                'testing': ["http://testing_endpoint"],
                'development': ["http://development_endpoint"],
                'production': ["http://production_endpoint"],
                'staging': ["http://staging_endpoint"]
            },
            {
                'development': "http://development_test_data"
            },
            (
                "http://development_endpoint",
                "development",
                "http://development_test_data"
            )
        ),
        (   # Query 11 - full server_urls for x-maturity; JSON object text_data_location with one x-maturity + default
            {
                'testing': ["http://testing_endpoint"],
                'development': ["http://development_endpoint"],
                'production': ["http://production_endpoint"],
                'staging': ["http://staging_endpoint"]
            },
            {
                'default': "http://default_test_data",
                'development': "http://development_test_data"
            },
            (
                "http://development_endpoint",
                "development",
                "http://development_test_data"
            )
        ),
        (   # Query 12 - full server_urls for x-maturity;
            #            JSON object text_data_location with one x-maturity  with list of test data URLs
            {
                'testing': ["http://testing_endpoint"],
                'development': ["http://development_endpoint"],
                'production': ["http://production_endpoint"],
                'staging': ["http://staging_endpoint"]
            },
            {
                'development': [
                    "http://development_test_data_1",
                    "http://development_test_data_2"
                ]
            },
            (
                "http://development_endpoint",
                "development",
                [
                    "http://development_test_data_1",
                    "http://development_test_data_2"
                ]
            )
        )
    ]
)
def test_select_endpoint(query: Tuple):
    assert select_endpoint(query[0], query[1], check_access=False) == query[2]


@pytest.mark.parametrize(
    "server_urls,test_data_location,outcome,endpoint,x_maturity,test_data",
    [
        (   # Query 0 - resolvable endpoint for a defined 'x-maturity'
            # These particular test details are valid and the indicated TRAPI endpoint 'alive' as of
            # 15 May 2023, but may need to be revised in the future, as Translator resources evolve?
                {   # server_url
                'development': [f'{TEST_KP_BASEURL}{DEF_M_M_TRAPI}'],
            },
                {   # test_data_location
                'development': KP_TEST_DATA_URL
            },
                True,  # outcome
            f'{TEST_KP_BASEURL}{DEF_M_M_TRAPI}',  # endpoint
            "development",  # x_maturity
                KP_TEST_DATA_URL   # test_data
        ),
        (   # Query 1 - resolvable endpoint test data resolved from a default
            # These particular test details are valid and the indicated TRAPI endpoint 'alive' as of
            # 15 May 2023, but may need to be revised in the future, as Translator resources evolve?
                {   # server_url
                'development': [f'{TEST_KP_BASEURL}{DEF_M_M_TRAPI}'],
            },
                {   # test_data_location
                'default': KP_TEST_DATA_URL
            },
                True,  # outcome
            f'{TEST_KP_BASEURL}{DEF_M_M_TRAPI}',  # endpoint
            "development",  # x_maturity
                KP_TEST_DATA_URL   # test_data
        ),
        (   # Query 2 - unresolvable endpoint test data - no available test data for the specified 'x-maturity'?
            {  # server_url
                'development': [f'{TEST_KP_BASEURL}{DEF_M_M_TRAPI}'],
            },
            {  # test_data_location
                'testing': KP_TEST_DATA_URL
            },
            False,  # outcome
            "",
            "",
            ""
        ),
        (   # Query 3 - unresolvable since TRAPI 1.2 endpoint is no longer live for the specified 'x-maturity'?
            {  # server_url
                'development': [f'{TEST_KP_BASEURL}1.2'],  # ancient defunct endpoint
            },
            {  # test_data_location
                'default': KP_TEST_DATA_URL
            },
            False,  # outcome
            "",
            "",
            ""
        ),
    ]
)
def test_select_endpoint_with_checking(
        server_urls: Dict[str, List[str]],
        test_data_location: Optional[Union[str, List, Dict]],
        outcome: bool,
        endpoint: str,
        x_maturity: str,
        test_data: Union[str, List[str]]
):
    endpoint_details = select_endpoint(server_urls, test_data_location)
    if outcome:
        assert endpoint_details is not None
        assert endpoint_details[0] == endpoint
        assert endpoint_details[1] == x_maturity
        assert endpoint_details[2] == test_data
    else:
        assert endpoint_details is None


@pytest.mark.parametrize(
    "query",
    [
        (None, ''),  # Empty URL - just ignored
        ('', ''),    # Empty URL - just ignored
        (  # Github page URL
                'https://github.com/my_org/my_repo/blob/master/test/data/Test_data.json',
                'https://raw.githubusercontent.com/my_org/my_repo/master/test/data/Test_data.json'
        ),
        (  # Git raw URL
                'https://raw.githubusercontent.com/my_org/my_repo/master/test/data/Test_data.json',
                'https://raw.githubusercontent.com/my_org/my_repo/master/test/data/Test_data.json'
        ),
        (  # Non-Github URL
                'https://my_domain/Test_data.json',
                'https://my_domain/Test_data.json'
        )
    ]
)
def test_github_url_rewrite(query):
    rewritten_url = rewrite_github_url(query[0])
    assert rewritten_url == query[1]


def test_default_empty_query():
    registry_data = query_smart_api()
    assert len(registry_data) > 0, "Default query failed"


_QUERY_SMART_API_EXCEPTION_PREFIX = "Translator SmartAPI Registry Access Exception:"


def test_fake_url():
    registry_data: Dict = query_smart_api(url="fake URL")
    assert registry_data and "Error" in registry_data, "Missing error message?"
    assert registry_data["Error"].startswith(_QUERY_SMART_API_EXCEPTION_PREFIX), "Unexpected error message?"


def test_query_smart_api():
    registry_data = query_smart_api(parameters=SMARTAPI_QUERY_PARAMETERS)
    assert "total" in registry_data, f"\tMissing 'total' tag in results?"
    assert registry_data["total"] > 0, f"\tZero 'total' in results?"
    assert "hits" in registry_data, f"\tMissing 'hits' tag in results?"
    for index, service in enumerate(registry_data['hits']):
        if "info" not in service:
            logger.debug(f"\tMissing 'hits' tag in hit entry? Ignoring entry...")
            continue
        info = service["info"]
        if "title" not in info:
            logger.debug(f"\tMissing 'title' tag in 'hit.info'? Ignoring entry...")
            continue
        title = info["title"]
        logger.debug(f"\n{index} - '{title}':")
        if "x-translator" not in info:
            logger.debug(f"\tMissing 'x-translator' tag in 'hit.info'? Ignoring entry...")
            continue
        x_translator = info["x-translator"]
        if "component" not in x_translator:
            logger.debug(f"\tMissing 'component' tag in 'hit.info.x-translator'? Ignoring entry...")
            continue
        component = x_translator["component"]
        if "x-trapi" not in info:
            logger.debug(f"\tMissing 'x-trapi' tag in 'hit.info'? Ignoring entry...")
            continue
        x_trapi = info["x-trapi"]

        if component == "KP":
            if "test_data_location" not in x_trapi:
                logger.debug(f"\tMissing 'test_data_location' tag in 'hit.info.x-trapi'? Ignoring entry...")
                continue
            else:
                test_data_location = x_trapi["test_data_location"]
                logger.debug(f"\t'hit.info.x-trapi.test_data_location': '{test_data_location}'")
        else:
            logger.debug(f"\tIs an ARA?")


def test_empty_json_data():
    value = tag_value({}, "testing.one.two.three")
    assert not value


_TEST_JSON_DATA = {
        "testing": {
            "one": {
                "two": {
                    "three": "The End!"
                },

                "another_one": "for_fun"
            }
        }
    }


def test_valid_tag_path():
    value = tag_value(_TEST_JSON_DATA, "testing.one.two.three")
    assert value == "The End!"


def test_empty_tag_path():
    value = tag_value(_TEST_JSON_DATA, "")
    assert not value


def test_missing_intermediate_tag_path():
    value = tag_value(_TEST_JSON_DATA, "testing.one.four.five")
    assert not value


def test_missing_end_tag_path():
    value = tag_value(_TEST_JSON_DATA, "testing.one.two.three.four")
    assert not value


def _wrap_infores(infores: str):
    return {
        "info": {
            "title": "test_source_of_interest",
            "x-translator": {
                    "infores": infores
            }
        }
    }


@pytest.mark.parametrize(
    "query",
    [
        # the <infores> from the Registry is assumed to be non-empty (see usage in main code...)
        # (<infores>, <target_sources>, <boolean return value>)
        (_wrap_infores("infores-object-id"), None, "infores-object-id"),   # Empty <target_sources>
        (_wrap_infores("infores-object-id"), set(), "infores-object-id"),  # Empty <target_sources>
        (_wrap_infores("infores-object-id"), {"infores-object-id"}, "infores-object-id"),  # single matching element in 'target_source' set
        (_wrap_infores("infores-object-id"), {"infores-*"}, "infores-object-id"),   # match to single prefix wildcard pattern in 'target_source' set
        (_wrap_infores("infores-object-id"), {"*-object-id"}, "infores-object-id"),  # match to single suffix wildcard pattern in 'target_source' set
        (_wrap_infores("infores-object-id"), {"infores-*-id"}, "infores-object-id"),   # match to embedded wildcard pattern in 'target_source' set
        (_wrap_infores("infores-object-id"), {"infores-*-ID"}, None),  # mismatch to embedded wildcard pattern in 'target_source' set
        (_wrap_infores("infores-object-id"), {"infores-*-*"}, None),   # only matches a single embedded wildcard pattern...
        (_wrap_infores("infores-object-id"), {"another-*"}, None),  # mismatch to single wildcard pattern in 'target_source' set
        (
            # exact match to single element in the 'target_source' set
            _wrap_infores("infores-object-id"),
            {
                "another-infores-object-id",
                "infores-object-id",
                "yetanuder-infores-id"
            },
            "infores-object-id"
        ),
        (
            # missing match to single element in the 'target_source' set
            _wrap_infores("infores-object-id"),
            {
                "another-infores-object-id",
                "yetanuder-infores-id"
            },
            None
        ),
        (   # missing match to single wildcard pattern
            # embedded in the 'target_source' set
            _wrap_infores("infores-object-id"),
            {
                "another-infores-object-id",
                "yetanuder-*",
                "some-other-infores-id"
            },
            None
        ),
    ]
)
def test_source_of_interest(query: Tuple):
    assert source_of_interest(service=query[0], target_sources=query[1]) is query[2]


def assert_tag(metadata: Dict, service: str, tag: str):
    assert tag in metadata[service], f"Missing tag {tag} in metadata of service '{service}'?"


def shared_test_extract_component_test_data_metadata_from_registry(
        query: Tuple[Dict, str, str],
        component_type: str
):
    assert component_type in ["KP", "ARA"]
    service_metadata: Dict[str, Dict[str,  Optional[str]]] = \
        extract_component_test_metadata_from_registry(query[0], component_type=component_type)

    # Test expectation of missing 'test_data_location' key => expected missing metadata
    if not query[1]:
        assert len(service_metadata) == 0, f"Expecting empty {component_type} service metadata result?"
    else:
        assert len(service_metadata) != 0, f"Expecting a non-empty {component_type} service metadata result?"

        assert query[1] in service_metadata, \
            f"Missing test_data_location '{query[1]}' expected in {component_type} '{service_metadata}' dictionary?"

        assert_tag(service_metadata, query[1], "url")
        assert query[2] in service_metadata[query[1]]['url']
        assert_tag(service_metadata, query[1], "service_title")
        assert_tag(service_metadata, query[1], "service_version")
        assert_tag(service_metadata, query[1], "infores")
        assert_tag(service_metadata, query[1], "biolink_version")
        assert_tag(service_metadata, query[1], "trapi_version")


# extract_kp_test_data_metadata_from_registry(registry_data) -> Dict[str, str]
@pytest.mark.parametrize(
    "query",
    [
        (  # Query 0 - Valid 'hits' entry with non-empty 'info.x-trapi.test_data_location'
            {
                "hits": [
                    {
                        'info': {
                            'contact': {
                                'email': 'translator@broadinstitute.org',
                                'name': 'Molecular Data Provider',
                                'x-role': 'responsible organization'
                            },
                            'description': 'Molecular Data Provider for NCATS Biomedical Translator',
                            'title': 'MolePro',
                            'version': f'{DEF_M_M_TRAPI}.0.0',
                            'x-translator': {
                                'biolink-version': '3.2.0',
                                'component': 'KP',
                                'infores': 'infores:molepro',
                                'team': ['Molecular Data Provider']
                            },
                            'x-trapi': {
                                'test_data_location': 'https://github.com/broadinstitute/molecular-data-provider' +
                                                      '/blob/master/test/data/MolePro-test-data.json',
                                'version': DEF_M_M_P_TRAPI
                            }
                        },
                        'servers': [
                            {
                                'description': 'TRAPI production service for MolePro',
                                'url': f'https://molepro-trapi.transltr.io/molepro/trapi/v{DEF_M_M_TRAPI}',
                                'x-maturity': 'production'
                            },
                            {
                                'description': 'TRAPI test service for MolePro',
                                'url': f'https://molepro-trapi.test.transltr.io/molepro/trapi/v{DEF_M_M_TRAPI}',
                                'x-maturity': 'testing'
                            },
                            {
                                'description': 'TRAPI staging service for MolePro',
                                'url': f'https://molepro-trapi.ci.transltr.io/molepro/trapi/v{DEF_M_M_TRAPI}',
                                'x-maturity': 'staging'
                            },
                            {
                                'description': 'TRAPI development service for MolePro',
                                'url': f'{TEST_KP_BASEURL}{DEF_M_M_TRAPI}',
                                'x-maturity': 'development'
                            }
                        ],
                    }
                ]
            },
            f'molepro,{DEF_M_M_P_TRAPI},3.2.0',  # KP test_data_location, converted to Github raw data link
            f'{TEST_KP_BASEURL}{DEF_M_M_TRAPI}'  # 'production' endpoint url preferred for testing?
        ),
        (   # Query 1 - Empty "hits" List
            {
                "hits": []
            },
            None, None
        ),
        (   # Query 2 - Empty "hits" entry
            {
                "hits": [{}]
            },
            None, None
        ),
        (   # Query 3 - "hits" entry with missing 'component' (and 'infores')
            {
                "hits": [
                    {
                        "info": {
                        }
                    }
                ]
            },
            None, None
        ),
        (   # Query 4 - "hits" ARA component entry
            {
                "hits": [
                    {
                        "info": {
                            "x-translator": {
                                "infores": "infores:some-ara",
                                "component": "ARA"
                            }
                        }
                    }
                ]
            },
            None, None
        ),
        (   # Query 5 - "hits" KP component entry with missing 'infores'
            {
                "hits": [
                    {
                        "info": {
                            "x-translator": {
                                "infores": "infores:some-kp"
                            }
                        }
                    }
                ]
            },
            None, None
        ),
        (   # Query 6 - "hits" KP component entry with missing 'info.x-trapi'
            {
                "hits": [
                    {
                        "info": {
                            "title": "KP component entry with missing info.x-trapi",
                            "x-translator": {
                                "infores": "infores:some-kp",
                                "component": "KP"
                            }
                        }
                    }
                ]
            },
            None, None
        ),
        (   # Query 7 - "hits" KP component entry with missing info.x-trapi.test_data_location tag value
            {
                "hits": [
                    {
                        "info": {
                            "title": "KP component entry with missing info.x-trapi.test_data_location tag value",
                            "x-translator": {
                                "infores": "infores:some-kp",
                                "component": "KP"
                            },
                            "x-trapi": {

                            }
                        }
                    }
                ]
            },
            None, None
        )
    ]
)
def test_extract_kp_test_data_metadata_from_registry(query: Tuple[Dict, str, str]):
    shared_test_extract_component_test_data_metadata_from_registry(query, "KP")


# extract_kp_test_data_metadata_from_registry(registry_data) -> Dict[str, str]
@pytest.mark.parametrize(
    "query",
    [
        (  # Query 0 - Valid 'hits' ARA entry with non-empty 'info.x-trapi.test_data_location'
            {
                "hits": [
                    {
                        'info': {
                            'contact': {
                                'email': 'edeutsch@systemsbiology.org'
                            },
                            'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint for the NCATS Biomedical Translator Reasoner',
                            'license': {
                                'name': 'Apache 2.0',
                                'url': 'http://www.apache.org/licenses/LICENSE-2.0.html'
                            },
                            'termsOfService': 'https://github.com/RTXteam/RTX/blob/master/LICENSE',
                            'title': f'ARAX Translator Reasoner - TRAPI {DEF_M_M_P_TRAPI}',
                            'version': f"{DEF_M_M_P_TRAPI}",
                            'x-translator': {
                                'biolink-version': '3.2.0',
                                'component': 'ARA',
                                'infores': 'infores:arax',
                                'team': ['Expander Agent']
                            },
                            'x-trapi': {
                                'test_data_location':
                                    'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                                    'main/tests/onehop/test_triples/ARA/ARAX/ARAX_Lite.json',
                                'version': f"{DEF_M_M_P_TRAPI}"
                            }
                        },
                        'servers': [
                            {
                                'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - production',
                                'url': f'https://arax.ncats.io/api/arax/v{DEF_M_M_TRAPI}',
                                'x-maturity': 'production'
                            }, {
                                'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - testing',
                                'url': f'https://arax.test.transltr.io/api/arax/v{DEF_M_M_TRAPI}',
                                'x-maturity': 'testing'
                            }, {
                                'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - staging',
                                'url': f'https://arax.ci.transltr.io/api/arax/v{DEF_M_M_TRAPI}',
                                'x-maturity': 'staging'
                            }, {
                                'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - development',
                                'url': f'https://arax.ncats.io/beta/api/arax/v{DEF_M_M_TRAPI}',
                                'x-maturity': 'development'
                            },
                        ],
                    }
                ]
            },
            f'arax,{DEF_M_M_P_TRAPI},2.2.11',
            f'{ARA_TEST_DATA_URL}{DEF_M_M_TRAPI}'
        )
    ]
)
def test_extract_ara_test_data_metadata_from_registry(query: Tuple[Dict, str, str]):
    shared_test_extract_component_test_data_metadata_from_registry(query, "ARA")


# validate_testable_resource(index, service, component) -> Optional[Dict[str, Union[str, List, Dict]]]
@pytest.mark.parametrize(
    "query",
    [
        (  # query 0 - 'empty' service dictionary
            dict(),  # service
            False,   # True if expecting that resource_metadata is not None; False otherwise
            ""       # expected 'url'

        ),
        (   # query 1 - minimally 'complete' service dictionary implies that the resource is amenable to testing
            {
                'info': {
                    'title': f'ARAX Translator Reasoner - TRAPI {DEF_M_M_P_TRAPI}',
                    'x-translator': {
                        'infores': 'infores:arax',
                    },
                    'x-trapi': {
                        'test_data_location':
                            'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                            'main/tests/onehop/test_triples/ARA/ARAX/ARAX_Lite.json',
                    }
                },
                'servers': [
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - development',
                        'url': f'https://arax.ncats.io/beta/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'development'
                    }
                ],
            },       # service
            True,    # True if expecting that resource_metadata is not None; False otherwise
            f"https://arax.ncats.io/beta/api/arax/v{DEF_M_M_TRAPI}"  # expected testable endpoint (only 'development' available)
        ),
        (
            {  # query 2. missing service 'title' - won't return any resource_metadata
                'info': {
                    # 'title': f'ARAX Translator Reasoner - TRAPI {CURRENT_DEFAULT_MAJOR_MINOR_PATCH_TRAPI}',
                    'x-translator': {
                        'infores': 'infores:arax',
                    },
                    'x-trapi': {
                        'test_data_location':
                            'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                            'main/tests/onehop/test_triples/ARA/ARAX/ARAX_Lite.json',
                    }
                },
                'servers': [
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - development',
                        'url': f'https://arax.ncats.io/beta/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'development'
                    }
                ],
            },      # service
            False,  # True if expecting that resource_metadata is not None; False otherwise
            ""      # expected 'url'
        ),
        (
            {  # query 3. missing 'infores' - won't return any resource_metadata
                'info': {
                    'title': f'ARAX Translator Reasoner - TRAPI {DEF_M_M_P_TRAPI}',
                    'x-translator': {
                        # 'infores': 'infores:arax',
                    },
                    'x-trapi': {
                        'test_data_location':
                            'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                            'main/tests/onehop/test_triples/ARA/ARAX/ARAX_Lite.json',
                    }
                },
                'servers': [
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - development',
                        'url': f'https://arax.ncats.io/beta/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'development'
                    }
                ],
            },      # service
            False,  # True if expecting that resource_metadata is not None; False otherwise
            ""      # expected 'url'
        ),
        (
            {  # query 4. missing 'servers' block - won't return any resource_metadata
                'info': {
                    'title': f'ARAX Translator Reasoner - TRAPI {DEF_M_M_P_TRAPI}',
                    'x-translator': {
                        'infores': 'infores:arax',
                    },
                    'x-trapi': {
                        'test_data_location':
                            'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                            'main/tests/onehop/test_triples/ARA/ARAX/ARAX_Lite.json',
                    }
                }
            },      # service
            False,  # True if expecting that resource_metadata is not None; False otherwise
            ""      # expected 'url'
        ),
        (
            {  # query 5. empty 'servers' block - won't return any resource_metadata
                'info': {
                    'title': f'ARAX Translator Reasoner - TRAPI {DEF_M_M_P_TRAPI}',
                    'x-translator': {
                        'infores': 'infores:arax',
                    },
                    'x-trapi': {
                        'test_data_location':
                            'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                            'main/tests/onehop/test_triples/ARA/ARAX/ARAX_Lite.json',
                    }
                },
                'servers': [],
            },      # service
            False,  # True if expecting that resource_metadata is not None; False otherwise
            ""      # expected 'url'
        ),
        (
            {  # query 6. missing 'test_data_location' (i.e. not testable!)
                'info': {
                    'title': f'ARAX Translator Reasoner - TRAPI {DEF_M_M_P_TRAPI}',
                    'x-translator': {
                        # 'infores': 'infores:arax',
                    },
                    'x-trapi': {
                        # 'test_data_location':
                        #     'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                        #     'main/tests/onehop/test_triples/ARA/ARAX/ARAX_Lite.json',
                    }
                },
                'servers': [
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - development',
                        'url': f'https://arax.ncats.io/beta/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'development'
                    }
                ],
            },      # service
            False,  # True if expecting that resource_metadata is not None; False otherwise
            ""      # expected 'url'
        ),
        (
            {   # query 7. testable, simple single testdata URL; 'production' endpoint prioritized
                'info': {
                    'title': f'ARAX Translator Reasoner - TRAPI {DEF_M_M_P_TRAPI}',
                    'x-translator': {
                        'infores': 'infores:arax',
                    },
                    'x-trapi': {
                        'test_data_location':
                            'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                            'main/tests/onehop/test_triples/ARA/ARAX/ARAX_Lite.json',
                    }
                },
                'servers': [
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - development',
                        'url': f'https://arax.ncats.io/beta/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'development'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - testing',
                        'url': f'https://arax.test.transltr.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'testing'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - production',
                        'url': f'https://arax.ncats.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'production'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - staging',
                        'url': f'https://arax.ci.transltr.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'staging'
                    },

                ],
            },       # service
            True,    # True if expecting that resource_metadata is not None; False otherwise
            f"https://arax.ncats.io/api/arax/v{DEF_M_M_TRAPI}"  # expected 'url' is 'production'
        ),
        (
            {   # query 8. testable, simple single testdata URL; 'staging' endpoint has greatest precedence
                'info': {
                    'title': f'ARAX Translator Reasoner - TRAPI {DEF_M_M_P_TRAPI}',
                    'x-translator': {
                        'infores': 'infores:arax',
                    },
                    'x-trapi': {
                        'test_data_location':
                            'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                            'main/tests/onehop/test_triples/ARA/ARAX/ARAX_Lite.json',
                    }
                },
                'servers': [
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - development',
                        'url': f'https://arax.ncats.io/beta/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'development'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - staging',
                        'url': f'https://arax.ci.transltr.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'staging'
                    }
                ],
            },       # service
            True,    # True if expecting that resource_metadata is not None; False otherwise
            f"https://arax.ci.transltr.io/api/arax/v{DEF_M_M_TRAPI}"  # expected 'url' is 'staging'
        ),
        (
            {   # query 9. testable, list of URLs, uses only first one; 'production' endpoint prioritized
                'info': {
                    'title': f'ARAX Translator Reasoner - TRAPI {DEF_M_M_P_TRAPI}',
                    'x-translator': {
                        'infores': 'infores:arax',
                    },
                    'x-trapi': {
                        'test_data_location': [
                            'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                            'main/tests/onehop/test_triples/ARA/Unit_Test_ARA/Test_ARA.json',
                            'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                            'main/tests/onehop/test_triples/ARA/ARAX/ARAX_Lite.json'
                        ]
                    }
                },
                'servers': [
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - development',
                        'url': f'https://arax.ncats.io/beta/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'development'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - testing',
                        'url': f'https://arax.test.transltr.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'testing'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - production',
                        'url': f'https://arax.ncats.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'production'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - staging',
                        'url': f'https://arax.ci.transltr.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'staging'
                    },

                ],
            },       # service
            True,    # True if expecting that resource_metadata is not None; False otherwise
            f"https://arax.ncats.io/api/arax/v{DEF_M_M_TRAPI}"  # expected 'url' is 'production' with unclassified list of data urls
        ),
        (
            {   # query 10. testable, x-maturity dictionary with default; 'production' endpoint prioritized
                'info': {
                    'title': f'ARAX Translator Reasoner - TRAPI {DEF_M_M_P_TRAPI}',
                    'x-translator': {
                        'infores': 'infores:arax',
                    },
                    'x-trapi': {
                        'test_data_location': {
                            "default": {
                                'url': 'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                                       'main/tests/onehop/test_triples/ARA/Unit_Test_ARA/Test_ARA.json'
                            }
                        }
                    }
                },
                'servers': [
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - development',
                        'url': f'https://arax.ncats.io/beta/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'development'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - testing',
                        'url': f'https://arax.test.transltr.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'testing'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - production',
                        'url': f'https://arax.ncats.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'production'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - staging',
                        'url': f'https://arax.ci.transltr.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'staging'
                    },

                ],
            },       # service
            True,    # True if expecting that resource_metadata is not None; False otherwise
            f"https://arax.ncats.io/api/arax/v{DEF_M_M_TRAPI}"  # expected 'url' is the 'production' since it can use 'default' data
        ),
        (
            {   # query 11. testable, x-maturity dictionary with 'testing' x-maturity
                #           but without default; 'testing' endpoint prioritized
                'info': {
                    'title': f'ARAX Translator Reasoner - TRAPI {DEF_M_M_P_TRAPI}',
                    'x-translator': {
                        'infores': 'infores:arax',
                    },
                    'x-trapi': {
                        'test_data_location': {
                            "testing": {
                                'url': 'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                                       'main/tests/onehop/test_triples/ARA/ARAX/ARAX_Lite.json'
                            }
                        }
                    }
                },
                'servers': [
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - development',
                        'url': f'https://arax.ncats.io/beta/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'development'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - testing',
                        'url': f'https://arax.test.transltr.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'testing'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - production',
                        'url': f'https://arax.ncats.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'production'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - staging',
                        'url': f'https://arax.ci.transltr.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'staging'
                    },

                ],
            },       # service
            True,    # True if expecting that resource_metadata is not None; False otherwise
            f"https://arax.test.transltr.io/api/arax/v{DEF_M_M_TRAPI}"  # expected 'url' is the 'testing' endpoint
        ),
        (
            {   # query 12. testable, x-maturity dictionary with 'testing' x-maturity but without default;
                # but since 'testing' servers endpoint is not specified, cannot test... return None
                'info': {
                    'title': f'ARAX Translator Reasoner - TRAPI {DEF_M_M_P_TRAPI}',
                    'x-translator': {
                        'infores': 'infores:arax',
                    },
                    'x-trapi': {
                        'test_data_location': {
                            "testing": {
                                'url': 'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                                       'main/tests/onehop/test_triples/ARA/ARAX/ARAX_Lite.json'
                            }
                        }
                    }
                },
                'servers': [
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - development',
                        'url': f'https://arax.ncats.io/beta/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'development'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - production',
                        'url': f'https://arax.ncats.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'production'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - staging',
                        'url': f'https://arax.ci.transltr.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'staging'
                    },

                ],
            },      # service
            False,  # True if expecting that resource_metadata is not None; False otherwise
            ""      # expected 'url'
        )
    ]
)
def test_validate_testable_resource(query: Tuple):
    resource_metadata: Optional[Dict[str, Union[str, List]]] = \
        validate_testable_resource(1, query[0], "ARA")
    if query[1]:
        assert 'url' in resource_metadata
        assert query[2] in resource_metadata['url']
    else:
        assert not resource_metadata


# validate_testable_resource(index, service, component) -> Optional[Dict[str, Union[str, List, Dict]]]
@pytest.mark.parametrize(
    "query",
    [
        # query[0] == service dictionary
        # query[1] ==  target infores if expecting that result is not None; None otherwise
        # query[2] ==  expected List of testable 'x-maturities' (ignored if None result expected)

        (  # query 0 - 'empty' service dictionary
            dict(),  # service
            None,    # True if expecting that resource_metadata is not None; False otherwise
            [""]     # expected 'x-maturities'
        ),
        (  # query 1 - minimally 'complete' service dictionary implies that the resource is amenable to testing
            {
                'info': {
                    'title': f'ARAX Translator Reasoner - TRAPI {DEF_M_M_P_TRAPI}',
                    'x-translator': {
                        'infores': 'infores:arax',
                    },
                    'x-trapi': {
                        'test_data_location':
                            'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                            'main/tests/onehop/test_triples/ARA/ARAX/ARAX_Lite.json',
                    }
                },
                'servers': [
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - development',
                        'url': f'https://arax.ncats.io/beta/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'development'
                    }
                ],
            },  # service
            "arax",
            ["development"]  # expected testable endpoint (only 'development' available)
        ),
        (
            {  # query 2. missing 'infores' - won't return any resource_metadata
                'info': {
                    'title': f'ARAX Translator Reasoner - TRAPI {DEF_M_M_P_TRAPI}',
                    'x-translator': {
                        # 'infores': 'infores:arax',
                    },
                    'x-trapi': {
                        'test_data_location':
                            'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                            'main/tests/onehop/test_triples/ARA/ARAX/ARAX_Lite.json',
                    }
                },
                'servers': [
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - development',
                        'url': f'https://arax.ncats.io/beta/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'development'
                    }
                ],
            },
            None,
            [""]
        ),
        (
            {  # query 3. missing 'servers' block - won't return any resource_metadata
                'info': {
                    'title': f'ARAX Translator Reasoner - TRAPI {DEF_M_M_P_TRAPI}',
                    'x-translator': {
                        'infores': 'infores:arax',
                    },
                    'x-trapi': {
                        'test_data_location':
                            'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                            'main/tests/onehop/test_triples/ARA/ARAX/ARAX_Lite.json',
                    }
                }
            },
            None,
            [""]
        ),
        (
            {  # query 4. empty 'servers' block - won't return any resource_metadata
                'info': {
                    'title': f'ARAX Translator Reasoner - TRAPI {DEF_M_M_P_TRAPI}',
                    'x-translator': {
                        'infores': 'infores:arax',
                    },
                    'x-trapi': {
                        'test_data_location':
                            'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                            'main/tests/onehop/test_triples/ARA/ARAX/ARAX_Lite.json',
                    }
                },
                'servers': [],
            },
            None,
            [""]
        ),
        (
            {  # query 5. missing 'test_data_location' (i.e. not testable!)
                'info': {
                    'title': f'ARAX Translator Reasoner - TRAPI {DEF_M_M_P_TRAPI}',
                    'x-translator': {
                        # 'infores': 'infores:arax',
                    },
                    'x-trapi': {
                        # 'test_data_location':
                        #     'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                        #     'main/tests/onehop/test_triples/ARA/ARAX/ARAX_Lite.json',
                    }
                },
                'servers': [
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - development',
                        'url': f'https://arax.ncats.io/beta/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'development'
                    }
                ],
            },
            None,
            [""]
        ),
        (
            {  # query 6. testable, simple single testdata URL; equivalent to all x-maturity environments testable
                'info': {
                    'title': f'ARAX Translator Reasoner - TRAPI {DEF_M_M_P_TRAPI}',
                    'x-translator': {
                        'infores': 'infores:arax',
                    },
                    'x-trapi': {
                        'test_data_location':
                            'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                            'main/tests/onehop/test_triples/ARA/ARAX/ARAX_Lite.json',
                    }
                },
                'servers': [
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - development',
                        'url': f'https://arax.ncats.io/beta/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'development'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - testing',
                        'url': f'https://arax.test.transltr.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'testing'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - production',
                        'url': f'https://arax.ncats.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'production'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - staging',
                        'url': f'https://arax.ci.transltr.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'staging'
                    },

                ],
            },
            "arax",
            ["production", "staging", "testing", "development"]
        ),
        (
            {  # query 7. testable, simple single testdata URL; servers only have 'staging' and 'development'
                'info': {
                    'title': f'ARAX Translator Reasoner - TRAPI {DEF_M_M_P_TRAPI}',
                    'x-translator': {
                        'infores': 'infores:arax',
                    },
                    'x-trapi': {
                        'test_data_location':
                            'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                            'main/tests/onehop/test_triples/ARA/ARAX/ARAX_Lite.json',
                    }
                },
                'servers': [
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - development',
                        'url': f'https://arax.ncats.io/beta/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'development'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - staging',
                        'url': f'https://arax.ci.transltr.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'staging'
                    }
                ],
            },
            "arax",
            ["staging", "development"]
        ),
        (
            {  # query 8. testable, list of URLs; equivalent to all x-maturity environments testable
                'info': {
                    'title': f'ARAX Translator Reasoner - TRAPI {DEF_M_M_P_TRAPI}',
                    'x-translator': {
                        'infores': 'infores:arax',
                    },
                    'x-trapi': {
                        'test_data_location': [
                            'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                            'main/tests/onehop/test_triples/ARA/Unit_Test_ARA/Test_ARA.json',
                            'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                            'main/tests/onehop/test_triples/ARA/ARAX/ARAX_Lite.json'
                        ]
                    }
                },
                'servers': [
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - development',
                        'url': f'https://arax.ncats.io/beta/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'development'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - testing',
                        'url': 'https://arax.test.transltr.io/api/arax/v{CURRENT_DEFAULT_MAJOR_MINOR_TRAPI}',
                        'x-maturity': 'testing'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - production',
                        'url': f'https://arax.ncats.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'production'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - staging',
                        'url': f'https://arax.ci.transltr.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'staging'
                    },

                ],
            },
            "arax",
            ["production", "staging", "testing", "development"]
        ),
        (
            {  # query 9. testable, x-maturity dictionary with default; all environments are testable
                'info': {
                    'title': f'ARAX Translator Reasoner - TRAPI {DEF_M_M_P_TRAPI}',
                    'x-translator': {
                        'infores': 'infores:arax',
                    },
                    'x-trapi': {
                        'test_data_location': {
                            "default": {
                                'url': 'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                                       'main/tests/onehop/test_triples/ARA/Unit_Test_ARA/Test_ARA.json'
                            }
                        }
                    }
                },
                'servers': [
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - development',
                        'url': f'https://arax.ncats.io/beta/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'development'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - testing',
                        'url': f'https://arax.test.transltr.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'testing'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - production',
                        'url': f'https://arax.ncats.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'production'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - staging',
                        'url': f'https://arax.ci.transltr.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'staging'
                    },
                ],
            },  # service
            "arax",
            ["production", "staging", "testing", "development"]
        ),
        (
            {  # query 10. testable, x-maturity dictionary with 'testing' x-maturity
                #           but without 'default'; 'testing' endpoint only is reported testable
                'info': {
                    'title': f'ARAX Translator Reasoner - TRAPI {DEF_M_M_P_TRAPI}',
                    'x-translator': {
                        'infores': 'infores:arax',
                    },
                    'x-trapi': {
                        'test_data_location': {
                            "testing": {
                                'url': 'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                                       'main/tests/onehop/test_triples/ARA/ARAX/ARAX_Lite.json'
                            }
                        }
                    }
                },
                'servers': [
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - development',
                        'url': f'https://arax.ncats.io/beta/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'development'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - testing',
                        'url': f'https://arax.test.transltr.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'testing'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - production',
                        'url': f'https://arax.ncats.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'production'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - staging',
                        'url': f'https://arax.ci.transltr.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'staging'
                    },

                ],
            },
            "arax",
            ["testing"]
        ),
        (
            {   # query 11. test data dictionary specified with 'testing' x-maturity but without default;
                # but since a 'testing' servers endpoint is not specified, cannot test... return None
                'info': {
                    'title': f'ARAX Translator Reasoner - TRAPI {DEF_M_M_P_TRAPI}',
                    'x-translator': {
                        'infores': 'infores:arax',
                    },
                    'x-trapi': {
                        'test_data_location': {
                            "testing": {
                                'url': 'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                                       'main/tests/onehop/test_triples/ARA/ARAX/ARAX_Lite.json'
                            }
                        }
                    }
                },
                'servers': [
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - development',
                        'url': f'https://arax.ncats.io/beta/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'development'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - production',
                        'url': f'https://arax.ncats.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'production'
                    },
                    {
                        'description': f'ARAX TRAPI {DEF_M_M_TRAPI} endpoint - staging',
                        'url': f'https://arax.ci.transltr.io/api/arax/v{DEF_M_M_TRAPI}',
                        'x-maturity': 'staging'
                    },

                ],
            },
            None,
            [""]
        )
    ]
)
def test_get_testable_resource(query: Tuple):
    resource: Optional[Tuple[str, List[str]]] = \
        get_testable_resource(1, query[0])
    if query[1]:
        assert resource[0] == query[1]
        assert all([x_maturity in query[2] for x_maturity in resource[1]])
    else:
        assert resource is None


def test_get_testable_resource_ids_from_registry():

    registry_data: Dict = get_the_registry_data()

    resources: Tuple[Dict[str, List[str]], Dict[str, List[str]]] = \
        get_testable_resources_from_registry(registry_data)

    assert resources

    assert len(resources[0]) > 0, \
        "No 'KP' services found with a 'test_data_location' value in the Translator SmartAPI Registry?"

    assert len(resources[1]) > 0, \
        "No 'ARA' services found with a 'test_data_location' value in the Translator SmartAPI Registry?"

    # 'molepro' and 'arax' are in both the MOCK and the
    # regular registry so these assertions should pass
    assert "molepro" in resources[0]
    assert "testing" in resources[0]["molepro"]
    assert "staging" in resources[0]["molepro"]
    assert "arax" in resources[1]
    assert "testing" in resources[1]["arax"]
    assert "production" in resources[1]["arax"]


def test_get_translator_kp_test_data_metadata():
    registry_data: Dict = get_the_registry_data()
    service_metadata = extract_component_test_metadata_from_registry(registry_data, "KP")
    assert len(service_metadata) > 0, \
        "No 'KP' services found with a 'test_data_location' value in the Translator SmartAPI Registry?"


def test_get_one_specific_target_kp():
    registry_data: Dict = get_the_registry_data()
    # we filter on the 'sri-reference-kg' since it is used both in the mock and real registry?
    service_metadata = extract_component_test_metadata_from_registry(registry_data, "KP", source="molepro")
    assert len(service_metadata) == 1, "We're expecting at least one but not more than one source KP here!"
    for service in service_metadata.values():
        assert service["infores"] == "molepro"
        assert f"{TEST_KP_BASEURL}{DEF_M_M_TRAPI}" in service["url"]


def test_get_translator_ara_test_data_metadata():
    registry_data: Dict = get_the_registry_data()
    service_metadata = extract_component_test_metadata_from_registry(registry_data=registry_data, component_type="ARA")
    assert len(service_metadata) > 0, \
        "No 'ARA' services found with a 'test_data_location' value in the Translator SmartAPI Registry?"


def test_get_one_specific_target_ara():
    registry_data: Dict = get_the_registry_data()
    # we filter on the 'arax' since it is used both in the mock and real registry?
    service_metadata = extract_component_test_metadata_from_registry(registry_data, "ARA", source="arax")
    assert len(service_metadata) == 1, "We're expecting at least one but not more than one source ARA here!"
    for service in service_metadata.values():
        assert service["infores"] == "arax"
        # the 'url' setting should be a list that includes urls from
        # the default 'production' x-maturity servers list
        assert f"https://arax.transltr.io/api/arax/v{DEF_M_M_TRAPI}" in service["url"]
        assert service["x_maturity"] == "production"


def test_get_one_specific_target_x_maturity_in_a_target_ara():
    registry_data: Dict = get_the_registry_data()
    # we filter on the 'arax' since it is used both in the mock and real registry?
    service_metadata = extract_component_test_metadata_from_registry(
        registry_data, "ARA", source="arax", x_maturity="testing"
    )
    assert len(service_metadata) == 1, "We're expecting at least one but not more than one source ARA here!"
    for service in service_metadata.values():
        assert service["infores"] == "arax"
        assert service["x_maturity"] == "testing"
        # the 'url' setting should be a list that includes urls from
        # the explicitly requested 'testing' x-maturity servers list
        assert f"https://arax.test.transltr.io/api/arax/v{DEF_M_M_TRAPI}" in service["url"]
