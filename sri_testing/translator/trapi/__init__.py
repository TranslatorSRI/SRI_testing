import warnings
from typing import Optional, Dict, List

from json import dumps

import requests

from reasoner_validator.versioning import SemVer
from reasoner_validator.report import ValidationReporter
from reasoner_validator.trapi import check_trapi_validity
from reasoner_validator import TRAPIResponseValidator

import pytest

import logging
logger = logging.getLogger(__name__)

# For testing, set TRAPI API query POST timeouts to 10 minutes == 600 seconds
DEFAULT_TRAPI_POST_TIMEOUT = 600.0

# Maximum number of input test edges to scrutinize in
# TRAPI response knowledge graph, during edge content tests
TEST_DATA_SAMPLE_SIZE = 10

# Default is actually specifically 1.3.0 as of September 2022
# but the reasoner_validator should discern this
DEFAULT_TRAPI_VERSION = "1.3.0"


def _output(json, flat=False):
    return dumps(json, sort_keys=False, indent=None if flat else 4)


class TrapiValidationWarning(UserWarning):
    pass


class UnitTestReport(ValidationReporter):
    """
    UnitTestReport is a wrapper for ValidationReporter used to aggregate SRI Test actionable validation messages.
    Not to be confused with the translator.sri.testing.report_db.TestReport, which is the comprehensive set
    of all JSON reports from a single SRI Testing harness test run.
    """

    def __init__(
            self,
            test_case: Dict,
            test_name: str,
            trapi_version: str,
            biolink_version: str,
            sources: Optional[Dict] = None,
            strict_validation: Optional[bool] = None
    ):
        error_msg_prefix = generate_test_error_msg_prefix(test_case, test_name=test_name)
        ValidationReporter.__init__(
            self,
            prefix=error_msg_prefix,
            trapi_version=trapi_version,
            biolink_version=biolink_version,
            sources=sources,
            strict_validation=strict_validation
        )

    # def test(self, is_true: bool, message: str, data_dump: Optional[str] = None):
    #     """
    #     Error test report.
    #
    #     :param is_true: test predicate, triggering error message report if False
    #     :param code: error message code reported when 'is_true' is False
    #     :param data_dump: optional extra information about a test failure (e.g. details about the object that failed)
    #     :raises: AssertionError when 'is_true' flag has value False
    #     """
    #     if not is_true:
    #         logger.error(message)
    #         if data_dump:
    #             logger.debug(data_dump)
    #         self.report(code)

    def skip(self, code: str, edge_id: str, messages: Optional[Dict] = None):
        """
        Edge test Pytest skipping wrapper.
        :param code: str, validation message code (indexed in the codes.yaml of the Reasoner Validator)
        :param edge_id: str, S-P-O identifier of the edge being skipped
        :param messages: (optional) additional validation messages available to explain why the test is being skipped
        :return:
        """
        self.report(code=code, edge_id=edge_id)
        if messages:
            self.add_messages(messages)
        report_string: str = self.dump_messages(flat=True)
        pytest.skip(reason=report_string)

    def assert_test_outcome(self):
        """
        Pytest Assertion wrapper: assert the Pytest outcome relative
        to the most severe ValidationReporter messages.
        """
        if self.has_errors():
            err_msg = self.dump_errors(flat=True)
            logger.error(err_msg)
            pytest.fail(reason=err_msg)
        elif self.has_warnings():
            wrn_msg = self.dump_warnings(flat=True)
            logger.error(wrn_msg)
            with pytest.warns(TrapiValidationWarning):
                warnings.warn(
                    TrapiValidationWarning(wrn_msg),
                    TrapiValidationWarning
                )
        elif self.has_information():
            logger.info(self.dump_info(flat=True))
            pass  # not yet sure what else to do here?
        else:
            pass  # do nothing... just passing through...


def generate_test_error_msg_prefix(case: Dict, test_name: str) -> str:
    assert case
    test_msg_prefix: str = "test_onehops.py::test_trapi_"
    resource_id: str = ""
    component: str = "kp"
    if 'ara_source' in case and case['ara_source']:
        component = "ara"
        ara_id = case['ara_source'].replace("infores:", "")
        resource_id += ara_id + "|"
    test_msg_prefix += f"{component}s["
    if 'kp_source' in case and case['kp_source']:
        kp_id = case['kp_source'].replace("infores:", "")
        resource_id += kp_id
    edge_idx = case['idx']
    edge_id = generate_edge_id(resource_id, edge_idx)
    if not test_name:
        test_name = "input"
    test_msg_prefix += f"{edge_id}-{test_name}] FAILED"
    return test_msg_prefix


async def call_trapi(url: str, trapi_message):
    """
    Given an url and a TRAPI message, post the message
    to the url and return the status and json response.

    :param url:
    :param trapi_message:
    :return:
    """
    query_url = f'{url}/query'

    # print(f"\ncall_trapi({query_url}):\n\t{dumps(trapi_message, sort_keys=False, indent=4)}", file=stderr, flush=True)

    try:
        response = requests.post(query_url, json=trapi_message, timeout=DEFAULT_TRAPI_POST_TIMEOUT)
    except requests.Timeout:
        # fake response object
        logger.error(
            f"call_trapi(\n\turl: '{url}',\n\ttrapi_message: '{_output(trapi_message)}') - Request POST TimeOut?"
        )
        response = requests.Response()
        response.status_code = 408
    except requests.RequestException as re:
        # perhaps another unexpected Request failure?
        logger.error(
            f"call_trapi(\n\turl: '{url}',\n\ttrapi_message: '{_output(trapi_message)}') - "
            f"Request POST exception: {str(re)}"
        )
        response = requests.Response()
        response.status_code = 408

    response_json = None
    if response.status_code == 200:
        try:
            response_json = response.json()
        except Exception as exc:
            logger.error(f"call_trapi({query_url}) JSON access error: {str(exc)}")

    return {'status_code': response.status_code, 'response_json': response_json}


def generate_edge_id(resource_id: str, edge_i: int) -> str:
    return f"{resource_id}#{str(edge_i)}"


def constrain_trapi_request_to_kp(trapi_request: Dict, kp_source: str) -> Dict:
    """
    Method to annotate KP constraint on an ARA call
    as an attribute_constraint object on the test edge.
    :param trapi_request: Dict, original TRAPI message
    :param kp_source: str, KP InfoRes (from kp_source field of test edge)
    :return: Dict, trapi_request annotated with additional KP 'attribute_constraint'
    """
    assert "message" in trapi_request
    message: Dict = trapi_request["message"]
    assert "query_graph" in message
    query_graph: Dict = message["query_graph"]
    assert "edges" in query_graph
    edges: Dict = query_graph["edges"]
    assert "ab" in edges
    edge: Dict = edges["ab"]

    # annotate the edge constraint on the (presumed single) edge object
    edge["attribute_constraints"] = [
        {
            "id": "biolink:knowledge_source",
            "name": "knowledge source",
            "value": [kp_source],
            "operator": "=="
        }
    ]

    return trapi_request


def case_node_found(target: str, identifier: str, case: Dict, nodes: Dict) -> bool:
    """
    Check for presence of the target identifier,
    with expected categories, in the "nodes" catalog.

    :param target: 'subject' or 'object'
    :param identifier: (CURIE) identifier of the node
    :param case: Dict, full test case (to access the target node 'category')
    :param nodes: Dict, nodes category indexed by node identifiers.
    :return:
    """
    #
    #     "nodes": {
    #         "MONDO:0005148": {"name": "type-2 diabetes"},
    #         "CHEBI:6801": {"name": "metformin", "categories": ["biolink:Drug"]}
    #     }
    #

    # Sanity check
    assert target in ["subject", "object"]

    if identifier in nodes.keys():
        # Found the target node identifier,
        # but is the expected category present?
        node_details = nodes[identifier]
        if "categories" in node_details:
            category = case[f"{target}_category"]
            if category in node_details["categories"]:
                return True

    # Target node identifier or categories is missing,
    # or not annotated with the expected category?
    return False


def case_result_found(
        subject_id: str,
        object_id: str,
        edge_id: str,
        results: List,
        trapi_version: str
) -> bool:
    """
    Validate that test case S--P->O edge is found bound to the Results?
    :param subject_id: str, subject node (CURIE) identifier
    :param object_id:  str, subject node (CURIE) identifier
    :param edge_id:  str, subject node (CURIE) identifier
    :param results: List of (TRAPI-version specific) Result objects
    :param trapi_version: str, target TRAPI version of the Response being validated
    :return: bool, True if case S-P-O edge was found in the results
    """
    trapi_1_4_0: bool = SemVer.from_string(trapi_version) >= SemVer.from_string("1.4.0")
    result_found: bool = False
    result: Dict

    def case_edge_bindings(target_edge_id: str, data: Dict) -> bool:
        """
        Check if target query edge id and knowledge graph edge id are in specified edge_bindings.
        :param target_edge_id:  str, expected knowledge edge identifier in a matching result
        :param data: TRAPI version-specific Response context from which the 'edge_bindings' may be retrieved
        :return: True, if found
        """
        edge_bindings: Dict = data["edge_bindings"]
        for bound_query_id, edge in edge_bindings.items():
            # The expected query identifier in this context is
            # hard coded in the 'one_hop.util.py' model
            if bound_query_id == "ab":
                for binding_details in edge:
                    if "id" in binding_details:
                        if target_edge_id == binding_details["id"]:
                            return True
        return False

    for result in results:

        # Node binding validation still currently same for recent TRAPI versions
        node_bindings: Dict = result["node_bindings"]
        subject_id_found: bool = False
        object_id_found: bool = False
        edge_id_found: bool = False
        for node in node_bindings.values():
            for details in node:
                if "id" in details:
                    if subject_id == details["id"]:
                        subject_id_found = True
                    elif object_id == details["id"]:
                        object_id_found = True

        # However, TRAPI 1.4.0 Message 'Results' 'edge_bindings' are reported differently
        #          from 1.3.0, rather, embedded in 'Analysis' objects (and 'Auxiliary Graphs')
        if trapi_1_4_0:
            #
            #     "auxiliary_graphs": {
            #         "a0": {
            #             "edges": [
            #                 "e02",
            #                 "e12"
            #             ]
            #         },
            #         "a1": {
            #             "edges": [
            #                 "extra_edge0"
            #             ]
            #         },
            #         "a2": {
            #             "edges" [
            #                 "extra_edge1"
            #             ]
            #         }
            #     },
            #     "results": [
            #         {
            #             "node_bindings": {
            #                 "n0": [
            #                     "id": "diabetes"
            #                 ],
            #                 "n1": [
            #                     "id": "metformin"
            #                 ]
            #             },
            #             "analyses":[
            #                 {
            #                     "reasoner_id": "ara0"
            #                     "edge_bindings": {
            #                         "e0": [
            #                             {
            #                                 "id": "e01"
            #                             },
            #                             {
            #                                 "id": "creative_edge"
            #                             }
            #                         ]
            #                     },
            #                     "support_graphs": [
            #                         "a1",
            #                         "a2"
            #                     ]
            #                     "score": .7
            #                 },
            #             ]
            #         }
            #     ]

            # result["analyses"] may be empty but prior TRAPI 1.4.0 schema validation ensures that
            # the "analysis" key is at least present plus the objects themselves are 'well-formed'
            analyses: List = result["analyses"]
            for analysis in analyses:
                edge_id_found = case_edge_bindings(edge_id, analysis)
                if edge_id_found:
                    break
        else:
            # TRAPI 1.3.0 or earlier?
            #
            # Then, the TRAPI 1.3.0 Message Results (referencing the
            # Response Knowledge Graph) could be something like this:
            #
            #     "results": [
            #         {
            #             "node_bindings": {
            #                # node "id"'s in knowledge graph, in edge "id"
            #                 "type-2 diabetes": [{"id": "MONDO:0005148"}],
            #                 "drug": [{"id": "CHEBI:6801"}]
            #             },
            #             "edge_bindings": {
            #                 # the edge binding key should be the query edge id
            #                 # bounded edge "id" is from knowledge graph
            #                 "treats": [{"id": "df87ff82"}]
            #             }
            #         }
            #     ]
            #
            edge_id_found = case_edge_bindings(edge_id, result)

        if subject_id_found and object_id_found and edge_id_found:
            result_found = True
            break

    return result_found


def case_input_found_in_response(case: Dict, response: Dict, trapi_version: str) -> bool:
    """
    Predicate to validate if test data test case specified edge is returned
    in the Knowledge Graph of the TRAPI Response Message. This method assumes
    that the TRAPI response is already generally validated as well-formed.

    :param case: Dict, input data test case
    :param response: Dict, TRAPI Response whose message ought to contain the test case edge
    :param trapi_version: str, TRAPI version of response being tested
    :return: True if test case edge found; False otherwise
    """
    # sanity checks
    assert case, "case_input_found_in_response(): Empty or missing test case data!"
    assert response, "case_input_found_in_response(): Empty or missing TRAPI Response!"
    assert "message" in response, "case_input_found_in_response(): TRAPI Response missing its Message component!"
    assert trapi_version

    #
    # case: Dict parameter contains something like:
    #
    #     idx: 0,
    #     subject_category: 'biolink:SmallMolecule',
    #     object_category: 'biolink:Disease',
    #     predicate: 'biolink:treats',
    #     subject_id: 'CHEBI:3002',  # may have the deprecated key 'subject' here
    #     object_id: 'MESH:D001249', # may have the deprecated key 'object' here
    #
    # the contents for which ought to be returned in
    # the TRAPI Knowledge Graph, as a Result mapping?
    #

    message: Dict = response["message"]
    if not (
        "knowledge_graph" in message and message["knowledge_graph"] and
        "results" in message and message["results"]
    ):
        # empty knowledge graph is syntactically ok, but in
        # this, input test data edge is automatically deemed missing
        return False

    # TODO: We need to check **here*** whether or not the
    #       TRAPI response returned the original test case edge!!?!!
    #       Not totally sure if we should first search the Results then
    #       the Knowledge Graph, or go directly to the Knowledge Graph...

    # The Message Query Graph could be something like:
    # "query_graph": {
    #     "nodes": {
    #         "type-2 diabetes": {"ids": ["MONDO:0005148"]},
    #         "drug": {"categories": ["biolink:Drug"]}
    #     },
    #     "edges": {
    #         "treats": {
    #             "subject": "drug",
    #             "predicates": ["biolink:treats"],
    #             "object": "type-2 diabetes"
    #         }
    #     }
    # }
    #
    # with a Response Message Knowledge Graph
    # dictionary with 'nodes' and 'edges':
    #
    # "knowledge_graph": {
    #     "nodes": ...,
    #     "edges": ...
    # }
    knowledge_graph: Dict = message["knowledge_graph"]

    # In the Knowledge Graph:
    #
    #     "nodes": {
    #         "MONDO:0005148": {"name": "type-2 diabetes"},
    #         "CHEBI:6801": {"name": "metformin", "categories": ["biolink:Drug"]}
    #     }
    #
    # Check for case 'subject_id' and 'object_id',
    # with expected categories, in nodes catalog
    nodes: Dict = knowledge_graph["nodes"]
    subject_id = case["subject"] if "subject" in case else case["subject_id"]
    if not case_node_found("subject", subject_id, case, nodes):
        # 'subject' node not found?
        return False

    object_id = case["object"] if "object" in case else case["object_id"]
    if not case_node_found("object", object_id, case, nodes):
        # 'object' node not found?
        return False

    # In the Knowledge Graph:
    #
    #     "edges": {
    #         "df87ff82": {
    #             "subject": "CHEBI:6801",
    #             "predicate": "biolink:treats",
    #             "object": "MONDO:0005148"
    #         }
    #     }
    #
    # Check in the edges catalog for an edge containing
    # the case 'subject_id', 'predicate' and 'object_id'
    edges: Dict = knowledge_graph["edges"]
    predicate = case["predicate"]
    edge_id_found: Optional[str] = None
    for edge_id, edge in edges.items():
        # Note: this edge search could be arduous on a big knowledge graph?
        if edge["subject"] == subject_id and \
                edge["predicate"] == predicate and \
                edge["object"] == object_id:
            edge_id_found = edge_id
            break

    if edge_id_found is None:
        # Test case S--P->O edge not found?
        return False

    results: List = message["results"]
    if not case_result_found(subject_id, object_id, edge_id_found, results, trapi_version):
        # Some components of test case S--P->O edge
        # NOT bound within any Results?
        return False

    # By this point, the case data assumed to be
    # successfully validated in the TRAPI Response?
    return True


async def execute_trapi_lookup(case, creator, rbag, test_report: UnitTestReport):
    """
    Method to execute a TRAPI lookup, using the 'creator' test template.

    :param case: input data test case
    :param creator: unit test-specific query message creator
    :param rbag: dictionary of results
    :param test_report: UnitTestReport(ValidationReporter), class wrapper object for asserting and reporting errors

    :return: None
    """
    trapi_request: Optional[Dict]
    output_element: Optional[str]
    output_node_binding: Optional[str]

    trapi_request, output_element, output_node_binding = creator(case)

    if not trapi_request:
        # output_element and output_node_binding were
        # expropriated by the 'creator' to return error information
        context = output_element.split("|")
        test_report.report(
            "error.trapi.request.invalid",
            identifier=context[1],
            context=context[0],
            reason=output_node_binding
        )
    else:
        # query use cases pertain to a particular TRAPI version
        trapi_version = case['trapi_version']
        biolink_version = case['biolink_version']

        # sanity check: verify first that the TRAPI request is well-formed by the creator(case)
        test_report.merge(check_trapi_validity(trapi_request, trapi_version=trapi_version))
        if not test_report.has_messages():
            # if no messages are reported, then continue with the validation

            if 'ara_source' in case and case['ara_source']:
                # sanity check!
                assert 'kp_source' in case and case['kp_source']

                # Here, we need annotate the TRAPI request query graph to
                # constrain an ARA query to the test case specified 'kp_source'
                trapi_request = constrain_trapi_request_to_kp(
                    trapi_request=trapi_request, kp_source=case['kp_source']
                )

            # Make the TRAPI call to the Case targeted KP or ARA resource, using the case-documented input test edge
            trapi_response = await call_trapi(case['url'], trapi_request)

            # Record the raw TRAPI query input and output for later test harness reference
            rbag.request = trapi_request
            rbag.response = trapi_response

            # Second sanity check: was the web service (HTTP) call itself successful?
            status_code: int = trapi_response['status_code']
            if status_code != 200:
                test_report.report("error.trapi.response.unexpected_http_code", identifier=status_code)
            else:
                #########################################################
                # Looks good so far, so now validate the TRAPI schemata #
                # and the Biolink "Semantic" compliance of the response #
                #########################################################
                response: Optional[Dict] = trapi_response['response_json']

                if response:
                    validator: TRAPIResponseValidator = TRAPIResponseValidator(
                        trapi_version=trapi_version,
                        biolink_version=biolink_version
                    )
                    validator.check_compliance_of_trapi_response(response=response)
                    test_report.merge(validator)

                #
                # case: Dict contains something like:
                #
                #     idx: 0,
                #     subject_category: 'biolink:SmallMolecule',
                #     object_category: 'biolink:Disease',
                #     predicate: 'biolink:treats',
                #     subject_id: 'CHEBI:3002',  # may have the deprecated key 'subject' here
                #     object_id: 'MESH:D001249', # may have the deprecated key 'object' here
                #
                # the contents for which ought to be returned in
                # the TRAPI Knowledge Graph, as a Result mapping?
                #
                if not case_input_found_in_response(case, response, trapi_version):
                    subject_id = case['subject'] if 'subject' in case else case['subject_id']
                    object_id = case['object'] if 'object' in case else case['object_id']
                    test_edge_id: str = f"{case['idx']}|({subject_id}#{case['subject_category']})" + \
                                        f"-[{case['predicate']}]->" + \
                                        f"({object_id}#{case['object_category']})"
                    test_report.report(
                        code="error.trapi.response.knowledge_graph.missing_expected_edge",
                        identifier=test_edge_id
                    )
