"""
Unit tests for OneHop unit test processing functions
"""
from typing import Dict

import pytest

from tests.onehop.util import get_unit_test_definitions
from sri_testing.translator.sri.testing.onehops_test_runner import (
    parse_unit_test_name,
    build_resource_summary_key,
    build_edge_details_key, build_recommendations_key
)


@pytest.mark.parametrize(
    "query",
    [
        (
            "KP",
            None,
            "Some_KP",
            "KP/Some_KP/resource_summary"
        ),
        (
            "ARA",
            "Some_ARA",
            "Some_KP",
            "ARA/Some_ARA/Some_KP/resource_summary"
        )
    ]
)
def test_get_resource_summary_key(query):
    edge_details_file_path = build_resource_summary_key(
        component=query[0], ara_id=query[1], kp_id=query[2]
    )
    assert edge_details_file_path == query[3]


@pytest.mark.parametrize(
    "query",
    [
        (
            "KP",
            None,
            "Some_KP",
            "2",
            "KP/Some_KP/Some_KP-2"
        ),
        (
            "ARA",
            "Some_ARA",
            "Some_KP",
            "3",
            "ARA/Some_ARA/Some_KP/Some_KP-3"
        )
    ]
)
def test_get_edge_details_key(query):
    edge_details_file_path = build_edge_details_key(
        component=query[0], ara_id=query[1], kp_id=query[2], edge_num=query[3]
    )
    assert edge_details_file_path == query[4]


@pytest.mark.parametrize(
    "query",
    [
        (
            "KP",
            None,
            "Some_KP",
            "KP/Some_KP/recommendations"
        ),
        (
            "ARA",
            "Some_ARA",
            "Some_KP",
            "ARA/Some_ARA/Some_KP/recommendations"
        )
    ]
)
def test_get_recommendations_key(query):
    edge_details_file_path = build_recommendations_key(
        component=query[0], ara_id=query[1], kp_id=query[2]
    )
    assert edge_details_file_path == query[3]


@pytest.mark.parametrize(
    "query",
    [
        (
            "test_onehops.py::test_trapi_kps[Test_KP_1#2-raise_object_by_subject]",
            "KP",
            None,
            "Test_KP_1",
            2,
            "raise_object_by_subject",
            "KP/Test_KP_1/Test_KP_1-2"
        ),
        (
            "test_onehops.py::test_trapi_aras[Test_ARA|Test_KP_1#3-raise_object_by_subject]",
            "ARA",
            "Test_ARA",
            "Test_KP_1",
            3,
            "raise_object_by_subject",
            "ARA/Test_ARA/Test_KP_1/Test_KP_1-3"
        )
    ]
)
def test_clean_up_unit_test_filename(query):
    # component, ara_id, kp_id, edge_num, test_id
    part = parse_unit_test_name(query[0])
    assert part[0] == query[1]  # component
    assert part[1] == query[2]  # ara_id
    assert part[2] == query[3]  # kp_id
    assert part[3] == query[4]  # int(edge_num)
    assert part[4] == query[5]  # test_id
    assert part[5] == query[6]  # edge_details_file_path


def test_get_unit_test_catalog():
    catalog: Dict = get_unit_test_definitions()
    assert catalog
    assert "by_subject" in catalog.keys()
    assert catalog["by_subject"] == "Given a known triple, create a TRAPI message " + \
                                    "that looks up the object by the subject"

