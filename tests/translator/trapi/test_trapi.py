"""
Unit tests for the generic (shared) components of the TRAPI testing utilities
"""
import logging
from typing import Tuple, Dict
from copy import deepcopy
import pytest

from sri_testing.translator.trapi import generate_test_error_msg_prefix, constrain_trapi_request_to_kp, \
    case_input_found_in_response, case_node_found

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


TEST_CASE = {
    "idx": 0,
    "subject_category": 'biolink:Drug',
    "object_category": 'biolink:Disease',
    "predicate": 'biolink:treats',
    "subject_id": 'CHEBI:6801',
    "object_id": 'MONDO:0005148'
}

TEST_CASE2 = TEST_CASE.copy()
TEST_CASE2["subject_category"] = 'biolink:SmallMolecule'

SAMPLE_KG_NODES = {
    "MONDO:0005148": {"name": "type-2 diabetes", "categories": ["biolink:Disease"]},
    "CHEBI:6801": {"name": "metformin", "categories": ["biolink:Drug"]}
}
SAMPLE_KG_NODES2 = deepcopy(SAMPLE_KG_NODES)
SAMPLE_KG_NODES2["MONDO:0005148"].pop("categories")


@pytest.mark.parametrize(
    "target,identifier,case,nodes,outcome",
    [
        (
            # query0 - Empty 'nodes'
            "subject",
            "CHEBI:6801",     # node identifier
            TEST_CASE,        # case
            dict(),           # empty nodes
            False             # outcome
        ),
        (
            # query1 - Nodes catalog containing the target (subject) node with complete annotation
            "subject",
            "CHEBI:6801",     # valid node identifier
            TEST_CASE,        # case
            SAMPLE_KG_NODES,  # non-empty sample nodes catalog
            True              # outcome
        ),
        (
            # query2 - Nodes catalog containing the target (object) node with missing category
            "object",
            "MONDO:0005148",   # valid node identifier
            TEST_CASE,         # case
            SAMPLE_KG_NODES2,  # sample nodes catalog missing in 'MONDO:0005148'
            False              # outcome
        ),
        (
            # query3 - Nodes catalog containing the target (object) node with incorrect category
            "subject",
            "CHEBI:6801",     # valid node identifier
            TEST_CASE2,       # case
            SAMPLE_KG_NODES,  # good sample nodes catalog
            False             # outcome
        )
    ]
)
def test_case_node_found(
        target,
        identifier: str,
        case: Dict,
        nodes: Dict,
        outcome: bool
):
    assert case_node_found(target, identifier, case, nodes) is outcome


SAMPLE_KG_EDGES = {
    "df87ff82": {
        "subject": "CHEBI:6801",
        "predicate": "biolink:treats",
        "object": "MONDO:0005148"
    }
}

SAMPLE_KG_EDGES2 = deepcopy(SAMPLE_KG_EDGES)
SAMPLE_KG_EDGES2["df87ff82"]["object"] = "MONDO:0001234"


SAMPLE_TRAPI_1_3_0_RESPONSE = {
    "message": {
        # we don't worry here about the query_graph for now
        "knowledge_graph": {
            "nodes": SAMPLE_KG_NODES,
            "edges": SAMPLE_KG_EDGES
        },
        "results": [
            {
                "node_bindings": {
                    # node "id"'s in knowledge graph, in edge "id"
                    "type-2 diabetes": [{"id": "MONDO:0005148"}],
                    "drug": [{"id": "CHEBI:6801"}]
                },
                "edge_bindings": {
                    # the edge binding key should be the query edge id
                    # bounded edge "id" is from knowledge graph
                    "ab": [{"id": "df87ff82"}]
                }
            }
        ]
    }
}

SAMPLE_TRAPI_1_3_0_RESPONSE2 = deepcopy(SAMPLE_TRAPI_1_3_0_RESPONSE)
SAMPLE_TRAPI_1_3_0_RESPONSE2["message"]["knowledge_graph"]["edges"] = SAMPLE_KG_EDGES2


SAMPLE_TRAPI_1_4_0_RESPONSE = {
    "message": {
        # we don't worry here about the query_graph for now
        "knowledge_graph": {
            "nodes": SAMPLE_KG_NODES,
            "edges": SAMPLE_KG_EDGES
        },
        "results": [
            {
                "node_bindings": {
                    # node "id"'s in knowledge graph, in edge "id"
                    "type-2 diabetes": [{"id": "MONDO:0005148"}],
                    "drug": [{"id": "CHEBI:6801"}]
                },
                "analyses": [
                    {
                        "reasoner_id": "infores:molepro",
                        "edge_bindings": {
                            "ab": [{"id": "df87ff82"}]
                        },
                        "support_graphs": [],
                        "score": ".7"
                    },
                ]
            }
        ]
    }
}


@pytest.mark.parametrize(
    "case,response,trapi_version,outcome",
    [
        (
            TEST_CASE,                    # case
            {   # query0 - empty TRAPI Response Message
                # (would be same failure with 1.4.0)
                "message": {

                }
            },
            "1.3.0",                     # TRAPI version
            False                        # expected outcome
        ),
        (
            TEST_CASE,                   # case
            {   # query1 - missing TRAPI Response Message Knowledge Graph key
                "message": {
                    # "knowledge_graph": {},
                    "results": []
                }
            },
            "1.4.0",                     # TRAPI version
            False                        # expected outcome
        ),
        (
            TEST_CASE,                   # case
            {   # query2 - missing TRAPI Response Message Results key
                "message": {
                    "knowledge_graph": {},
                    # "results": []
                }
            },
            "1.4.0",                     # TRAPI version
            False                        # expected outcome
        ),
        (
            TEST_CASE,                   # case
            {   # query3 - empty TRAPI Response Message Knowledge Graph and Results
                "message": {
                    "knowledge_graph": {},
                    "results": []
                }
            },
            "1.4.0",                     # TRAPI version
            False                        # expected outcome
        ),
        (   # query4 - fully compliant 1.3.0 Response
            TEST_CASE,                    # case
            SAMPLE_TRAPI_1_3_0_RESPONSE,  # response
            "1.3.0",                      # TRAPI version
            True                          # expected outcome
        ),
        (   # query5 - fully compliant 1.4.0 Response
            TEST_CASE,                    # case
            SAMPLE_TRAPI_1_4_0_RESPONSE,  # response
            "1.4.0",                      # TRAPI version
            True                          # expected outcome
        ),
        (   # query6 - fully compliant 1.3.0 Response but different test case category
            TEST_CASE2,                   # case
            SAMPLE_TRAPI_1_3_0_RESPONSE,  # response
            "1.3.0",                      # TRAPI version
            False                         # expected outcome
        ),
        (   # query7 - fully compliant 1.4.0 Response but different test case category
            TEST_CASE2,                   # case
            SAMPLE_TRAPI_1_4_0_RESPONSE,  # response
            "1.4.0",                      # TRAPI version
            False                         # expected outcome
        ),
        (   # query8 - fully compliant 1.3.0 Response but missing
            #          expected KG edge object identifier
            TEST_CASE,                     # case
            SAMPLE_TRAPI_1_3_0_RESPONSE2,  # response
            "1.3.0",                       # TRAPI version
            False                          # expected outcome
        )
    ]
)
def test_case_input_found_in_response(
        case: Dict,
        response: Dict,
        trapi_version: str,
        outcome: bool
):
    assert case_input_found_in_response(case, response, trapi_version) is outcome
