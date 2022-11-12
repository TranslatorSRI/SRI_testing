"""
Unit tests for Translator SmartAPI Registry
"""
from typing import Optional, Union, Tuple, Dict, List
import logging
import pytest

from translator.registry import (
    get_default_url,
    rewrite_github_url,
    query_smart_api,
    SMARTAPI_QUERY_PARAMETERS,
    tag_value,
    get_the_registry_data,
    extract_component_test_metadata_from_registry,
    get_testable_resource_ids_from_registry, source_of_interest
)

logger = logging.getLogger(__name__)

@pytest.mark.parametrize(
    "query",
    [
        (None, None),
        ("", None),
        (list(), None),
        (dict(), None),
        ("http://test_data", "http://test_data"),
        (
            [
                "http://first_test_data",
                "http://second_test_data"
            ],
            "http://first_test_data"
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


@pytest.mark.parametrize(
    "query",
    [
        # the <infores> from the Registry is assumed to be non-empty (see usage in main code...)
        # (<infores>, <target_sources>, <boolean return value>)
        ("infores-object-id", None, True),   # Empty <target_sources>
        ("infores-object-id", set(), True),  # Empty <target_sources>
        ("infores-object-id", {"infores-object-id"}, True),  # single matching element in 'target_source' set
        ("infores-object-id", {"infores-*"}, True),   # match to single prefix wildcard pattern in 'target_source' set
        ("infores-object-id", {"*-object-id"}, True),  # match to single suffix wildcard pattern in 'target_source' set
        ("infores-object-id", {"infores-*-id"}, True),   # match to embedded wildcard pattern in 'target_source' set
        ("infores-object-id", {"infores-*-ID"}, False),  # mismatch to embedded wildcard pattern in 'target_source' set
        ("infores-object-id", {"infores-*-*"}, False),   # only matches a single embedded wildcard pattern...
        ("infores-object-id", {"another-*"}, False),  # mismatch to single wildcard pattern in 'target_source' set
        (
            # exact match to single element in the 'target_source' set
            "infores-object-id",
            {
                "another-infores-object-id",
                "infores-object-id",
                "yetanuder-infores-id"
            },
            True
        ),
        (
            # missing match to single element in the 'target_source' set
            "infores-object-id",
            {
                "another-infores-object-id",
                "yetanuder-infores-id"
            },
            False
        ),
        (   # missing match to single wildcard pattern embedded in the 'target_source' set
            "infores-object-id",
            {
                "another-infores-object-id",
                "yetanuder-*",
                "someother-infores-id"
            },
            False
        ),
    ]
)
def test_source_of_interest(query: Tuple):
    assert source_of_interest(source=query[0], target_sources=query[1]) is query[2]


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
        assert service_metadata[query[1]]['url'] == query[2]
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
                            'version': '1.3.0.0',
                            'x-translator': {
                                'biolink-version': '2.4.7',
                                'component': 'KP',
                                'infores': 'infores:molepro',
                                'team': ['Molecular Data Provider']
                            },
                            'x-trapi': {
                                'test_data_location': 'https://github.com/broadinstitute/molecular-data-provider' +
                                                      '/blob/master/test/data/MolePro-test-data.json',
                                'version': '1.3.0'
                            }
                        },
                        'servers': [
                            {
                                'description': 'TRAPI production service for MolePro',
                                'url': 'https://molepro-trapi.transltr.io/molepro/trapi/v1.3',
                                'x-maturity': 'production'
                            },
                            {
                                'description': 'TRAPI test service for MolePro',
                                'url': 'https://molepro-trapi.test.transltr.io/molepro/trapi/v1.3',
                                'x-maturity': 'testing'
                            },
                            {
                                'description': 'TRAPI staging service for MolePro',
                                'url': 'https://molepro-trapi.ci.transltr.io/molepro/trapi/v1.3',
                                'x-maturity': 'staging'
                            },
                            {
                                'description': 'TRAPI development service for MolePro',
                                'url': 'https://translator.broadinstitute.org/molepro/trapi/v1.3',
                                'x-maturity': 'development'
                            }
                        ],
                    }
                ]
            },
            'molepro,1.3.0,2.4.7',   # KP test_data_location, converted to Github raw data link
            'https://molepro-trapi.transltr.io/molepro/trapi/v1.3'  # 'production' endpoint url preferred for testing?
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
                                'description': 'TRAPI 1.3 endpoint for the NCATS Biomedical Translator Reasoner called ARAX',
                                'license': {
                                    'name': 'Apache 2.0',
                                    'url': 'http://www.apache.org/licenses/LICENSE-2.0.html'
                                },
                                'termsOfService': 'https://github.com/RTXteam/RTX/blob/master/LICENSE',
                                'title': 'ARAX Translator Reasoner - TRAPI 1.3.0',
                                'version': '1.3.0',
                                'x-translator': {
                                    'biolink-version': '2.2.11',
                                    'component': 'ARA',
                                    'infores': 'infores:arax',
                                    'team': ['Expander Agent']
                                },
                                'x-trapi': {
                                    'test_data_location':
                                        'https://raw.githubusercontent.com/TranslatorSRI/SRI_testing/' +
                                        'main/tests/onehop/test_triples/ARA/ARAX/ARAX_Lite.json',
                                    'version': '1.3.0'
                                }
                            },
                            'servers': [
                                {
                                    'description': 'ARAX TRAPI 1.3 endpoint - production',
                                    'url': 'https://arax.ncats.io/api/arax/v1.3',
                                    'x-maturity': 'production'
                                }, {
                                    'description': 'ARAX TRAPI 1.3 endpoint - testing',
                                    'url': 'https://arax.test.transltr.io/api/arax/v1.3',
                                    'x-maturity': 'testing'
                                }, {
                                    'description': 'ARAX TRAPI 1.3 endpoint - staging',
                                    'url': 'https://arax.ci.transltr.io/api/arax/v1.3',
                                    'x-maturity': 'staging'
                                }, {
                                    'description': 'ARAX TRAPI 1.3 endpoint - development',
                                    'url': 'https://arax.ncats.io/beta/api/arax/v1.3',
                                    'x-maturity': 'development'
                                },
                            ],
                        }
                    ]
                },
                'arax,1.3.0,2.2.11',
                'https://arax.ncats.io/api/arax/v1.3'
        )
    ]
)
def test_extract_ara_test_data_metadata_from_registry(query: Tuple[Dict, str, str]):
    shared_test_extract_component_test_data_metadata_from_registry(query, "ARA")


def test_get_testable_resource_ids_from_registry():
    registry_data: Dict = get_the_registry_data()
    resources: Tuple[List[str], List[str]] = get_testable_resource_ids_from_registry(registry_data)
    assert resources
    assert len(resources[0]) > 0, \
        "No 'KP' services found with a 'test_data_location' value in the Translator SmartAPI Registry?"
    assert len(resources[1]) > 0, \
        "No 'ARA' services found with a 'test_data_location' value in the Translator SmartAPI Registry?"

    # 'molepro' and 'arax' are in both the MOCK and regular registry so these assertions should pass
    assert "molepro" in resources[0]
    assert "arax" in resources[1]


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


def test_get_translator_ara_test_data_metadata():
    registry_data: Dict = get_the_registry_data()
    service_metadata = extract_component_test_metadata_from_registry(registry_data, "ARA")
    assert len(service_metadata) > 0, \
        "No 'ARA' services found with a 'test_data_location' value in the Translator SmartAPI Registry?"


def test_get_one_specific_target_ara():
    registry_data: Dict = get_the_registry_data()
    # we filter on the 'arax' since it is used both in the mock and real registry?
    service_metadata = extract_component_test_metadata_from_registry(registry_data, "ARA", source="arax")
    assert len(service_metadata) == 1, "We're expecting at least one but not more than one source ARA here!"
    for service in service_metadata.values():
        assert service["infores"] == "arax"