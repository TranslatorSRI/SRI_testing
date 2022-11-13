import warnings
from typing import Optional, Dict

from json import dumps

import requests

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
            pass  # do nothing... just PASSing through...


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


async def execute_trapi_lookup(case, creator, rbag, test_report: UnitTestReport):
    """
    Method to execute a TRAPI lookup, using the 'creator' test template.

    :param case: input data test case
    :param creator: unit test-specific query message creator
    :param rbag: dictionary of results
    :param test_report: ErrorReport, class wrapper object for asserting and reporting errors

    :return: None
    """
    trapi_request: Optional[Dict]
    output_element: Optional[str]
    output_node_binding: Optional[str]

    trapi_request, output_element, output_node_binding = creator(case)

    if not trapi_request:
        # output_element and output_node_binding were expropriated by the 'creator' to return error information
        test_report.report("error.trapi.request.invalid", context=output_element, reason=output_node_binding)
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
                test_report.report("error.trapi.response.unexpected_http_code", status_code=status_code)
            else:
                ##########################################
                # Looks good so far, so now validate     #
                # the "Semantic" quality of the response #
                ##########################################
                response_message: Optional[Dict] = trapi_response['response_json']['message']

                if response_message:
                    validator: TRAPIResponseValidator = TRAPIResponseValidator(
                        trapi_version=trapi_version,
                        biolink_version=biolink_version
                    )
                    validator.check_compliance_of_trapi_response(message=response_message)
                    test_report.merge(validator)
