"""
Unit tests for the generic (shared) components of the TRAPI testing utilities
"""
import logging
from typing import Tuple, Dict

import pytest

from translator.trapi import generate_test_error_msg_prefix, constrain_trapi_request_to_kp

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "query",
    [
        (
                {
                    "kp_source": "infores:test-kp-1",
                    "idx": "2",
                },
                "test_name",
                "test_onehops.py::test_trapi_kps[test-kp-1#2-test_name] FAILED"
        ),
        (
                {
                    "kp_source": "infores:test-kp-1",
                    "idx": "2",
                },
                None,
                "test_onehops.py::test_trapi_kps[test-kp-1#2-input] FAILED"
        ),
        (
                {
                    "ara_source": "infores:test-ara",
                    "kp_source": "infores:test-kp-1",
                    "idx": "2",
                },
                "test_name",
                "test_onehops.py::test_trapi_aras[test-ara|test-kp-1#2-test_name] FAILED"
        ),
        (
                {
                    "ara_source": "infores:test-ara",
                    "kp_source": "infores:test-kp-1",
                    "idx": "2",
                },
                None,
                "test_onehops.py::test_trapi_aras[test-ara|test-kp-1#2-input] FAILED"
        )
    ]
)
def test_generate_test_error_msg_prefix(query: Tuple):
    prefix = generate_test_error_msg_prefix(case=query[0], test_name=query[1])
    assert prefix == query[2]


@pytest.mark.parametrize(
    "query",
    [
        (
            {
                "message": {
                    "query_graph": {
                        "nodes": {
                            'a': {
                                "categories": ['subject_category']
                            },
                            'b': {
                                "categories": ['object_category']
                            }
                        },
                        "edges": {
                            'ab': {
                                "subject": "a",
                                "object": "b",
                                "predicates": ['predicate']
                            }
                        }
                    },
                    'knowledge_graph': {
                        "nodes": {}, "edges": {},
                    },
                    'results': []
                }
            },
            "biolink:sri-reference-kg"
        )
    ]
)
def test_constrain_trapi_request_to_kp(query: Tuple):
    trapi_request: Dict = constrain_trapi_request_to_kp(
        trapi_request=query[0], kp_source=query[1]
    )
    assert trapi_request["message"]["query_graph"]["edges"]["ab"]["attribute_constraints"][0]["value"][0] == query[1]

