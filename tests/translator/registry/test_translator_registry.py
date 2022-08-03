"""
Unit tests for Translator SmartAPI Registry
"""
from typing import Optional, Tuple, Dict
import logging
import pytest

from translator.registry import (
    rewrite_github_url,
    query_smart_api,
    SMARTAPI_QUERY_PARAMETERS,
    tag_value,
    extract_component_test_metadata_from_registry,
    get_the_registry_data
)

logger = logging.getLogger(__name__)


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
                        "info": {
                            "title": "Some Valid KP",
                            "version": "0.0.1",
                            "x-translator": {
                                "infores": "infores:some-kp",
                                "component": "KP",
                                "team": "some-translator-team",
                                "biolink-version": "2.2.16"
                            },
                            "x-trapi": {
                                "version": "1.2.0",
                                "test_data_location": "http://some-kp-web-test-data-directory"
                            }
                        }
                    }
                ]
            },
            "http://some-kp-web-test-data-directory"  # test_data_location
        ),
        (   # Query 1 - Empty "hits" List
            {
                "hits": []
            },
            None
        ),
        (   # Query 2 - Empty "hits" entry
            {
                "hits": [{}]
            },
            None
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
            None
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
            None
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
            None
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
            None
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
            None
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
                            "info": {
                                "title": "Some Valid ARA",
                                "version": "0.0.1",
                                "x-translator": {
                                    "infores": "infores:some-ara",
                                    "component": "ARA",
                                    "team": "some-translator-team",
                                    "biolink-version": "2.2.16"
                                },
                                "x-trapi": {
                                    "version": "1.2.0",
                                    "test_data_location": "http://some-ara-web-test-data-directory"
                                }
                            }
                        }
                    ]
                },
                "http://some-ara-web-test-data-directory"   # test_data_location
        )
    ]
)
def test_extract_ara_test_data_metadata_from_registry(query: Tuple[Dict, str, str]):
    shared_test_extract_component_test_data_metadata_from_registry(query, "ARA")


def test_get_translator_kp_test_data_metadata():
    registry_data: Dict = get_the_registry_data()
    service_metadata = extract_component_test_metadata_from_registry(registry_data, "KP")
    assert len(service_metadata) > 0, \
        "No 'KP' services found with a 'test_data_location' value in the Translator SmartAPI Registry?"


def test_get_translator_ara_test_data_metadata():
    registry_data: Dict = get_the_registry_data()
    service_metadata = extract_component_test_metadata_from_registry(registry_data, "ARA")
    assert len(service_metadata) > 0, \
        "No 'ARA' services found with a 'test_data_location' value in the Translator SmartAPI Registry?"
