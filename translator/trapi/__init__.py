from typing import Optional, Dict, List, Iterable
from json import dumps

import logging
from pprint import PrettyPrinter

import requests
from jsonschema import ValidationError

from reasoner_validator import validate
from reasoner_validator.util import latest
from requests import Timeout, Response

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

pp = PrettyPrinter(indent=4)

# For testing, set TRAPI API query POST timeouts to 10 minutes == 600 seconds
DEFAULT_TRAPI_POST_TIMEOUT = 600.0

# Maximum number of edges to scrutinize in
# TRAPI response knowledge graph, during edge content tests
MAX_NO_OF_EDGES = 10

# TODO: We'd rather NOT hard code a default TRAPI here,
#       but do it for now pending clarity on how to guide
#       the choice of TRAPI from a Translator SmartAPI entry
# Default is actually specifically 1.2.0 as of March 2022,
# but the ReasonerAPI should discern this
DEFAULT_TRAPI_VERSION = "1"
_current_trapi_version = None


def set_trapi_version(version: str):
    global _current_trapi_version
    version = version if version else DEFAULT_TRAPI_VERSION
    _current_trapi_version = latest.get(version)
    logger.debug(f"TRAPI Version set to {_current_trapi_version}")


def get_trapi_version() -> Optional[str]:
    global _current_trapi_version
    return _current_trapi_version


def is_valid_trapi(instance, trapi_version):
    """Make sure that the Message is valid using reasoner_validator"""
    try:
        validate(
            instance=instance,
            component="Query",
            trapi_version=trapi_version
        )
        return True
    except ValidationError as e:
        import json
        # print(dumps(response_json, sort_keys=False, indent=4))
        print(e)
        return False


def check_provenance(ara_case, ara_response):
    """
    This is where we will check to see whether the edge
    in the ARA response is marked with the expected KP.
    But at the moment, there is not a standard way to do this.
    """
    kg = ara_response['knowledge_graph']
    edges: Dict[str, Dict] = kg['edges']

    kp_source_type = f"biolink:{ara_case['kp_source_type']}_knowledge_source"
    kp_infores = f"infores:{ara_case['kp_infores']}" if ara_case['kp_infores'] else ""

    number_of_edges_viewed = 0
    for edge in edges.values():

        # Every edge should always have at least *some* (provenance source) attributes
        if 'attributes' not in edge.keys():
            assert False, f"Edge '{pp.pformat(edge)}' has no attributes?"

        attributes = edge['attributes']

        # Expecting ARA and KP 'aggregator_knowledge_source' attributes?
        found_ara_knowledge_source = False
        found_kp_knowledge_source = False

        # TODO: is it acceptable to only have a 'knowledge_source' here?
        found_primary_or_original_knowledge_source = False

        for entry in attributes:

            attribute_type_id = entry['attribute_type_id']

            # Only examine provenance related attributes
            if attribute_type_id not in \
                    [
                        "biolink:aggregator_knowledge_source",
                        "biolink:primary_knowledge_source",
                        "biolink:original_knowledge_source"
                    ]:
                continue

            # TODO: there seems to be non-uniformity in provenance attribute values for some KP/ARA's
            #       in which a value is returned as a Python list (of at least one element?) instead of a string.
            #       Here, to ensure full coverage of the attribute values returned,
            #       we'll coerce scalar values into a list, then iterate.
            #
            try:
                value = entry['value']

                if isinstance(value, List):
                    if not value:
                        raise RuntimeError("an empty list?")

                elif isinstance(value, str):
                    value = [value]
                else:
                    RuntimeError("an unrecognized data type for attribute?")

                for infores in value:

                    if not infores.startswith("infores:"):
                        raise RuntimeError("not a well-formed InforRes CURIE")

                    if attribute_type_id == "biolink:aggregator_knowledge_source":

                        # Checking specifically here whether both KP and ARA infores
                        # attribute values are published as aggregator_knowledge_sources
                        if ara_case['ara_infores'] and infores == f"infores:{ara_case['ara_infores']}":
                            found_ara_knowledge_source = True

                        # check for special case of a KP provenance
                        if ara_case['kp_infores'] and \
                                attribute_type_id == kp_source_type and \
                                infores == kp_infores:
                            found_kp_knowledge_source = True
                    else:
                        # attribute_type_id is either a
                        # "biolink:primary_knowledge_source" or
                        # a "biolink:original_knowledge_source"

                        found_primary_or_original_knowledge_source = True

                        # check for special case of a KP provenance tagged this way
                        if ara_case['kp_infores'] and \
                                attribute_type_id == kp_source_type and \
                                infores == kp_infores:
                            found_kp_knowledge_source = True

            except RuntimeError as re:
                assert False, f"The Provenance Attribute value is {str(re)}, " + \
                              f"in Edge:\n'{pp.pformat(edge)}'\n"

        if ara_case['ara_infores'] and not found_ara_knowledge_source:
            assert False, f"'aggregator knowledge source' provenance missing for " +\
                          f"ARA '{ara_case['ara_infores'].upper()}' in Edge:\n{pp.pformat(edge)}\n"

        if ara_case['kp_infores'] and not found_kp_knowledge_source:
            assert False, f"'{ara_case['kp_source_type']}' provenance missing for " +\
                          f"KP '{ara_case['kp_source']}' in Edge:\n{pp.pformat(edge)}\n"

        if not found_primary_or_original_knowledge_source:
            assert False, "Neither 'primary' nor 'original' knowledge source' provenance attributes " +\
                          f"were found in Edge:\n'{pp.pformat(edge)}'\n from KP '{ara_case['kp_source']}' " \
                          f"accessed by ARA endpoint '{ara_case['url']}' "

        # We are not likely to want to check the entire Knowledge Graph for
        # provenance but only sample a subset, making the assumption that
        # defects in provenance will be systemic, thus will show up early
        number_of_edges_viewed += 1
        if number_of_edges_viewed >= MAX_NO_OF_EDGES:
            break


def call_trapi(url, opts, trapi_message):
    """Given an url and a TRAPI message, post the message to the url and return the status and json response"""

    query_url = f'{url}/query'

    # print(f"\ncall_trapi({query_url}):\n\t{dumps(trapi_message, sort_keys=False, indent=4)}", file=stderr, flush=True)

    try:
        response = requests.post(query_url, json=trapi_message, params=opts, timeout=DEFAULT_TRAPI_POST_TIMEOUT)
    except Timeout:
        # fake response object
        response = Response()
        response.status_code = 408

    response_json = None
    if response.status_code == 200:
        try:
            response_json = response.json()
        except Exception as exc:
            logger.error(f"call_trapi({query_url}) JSON access error: {str(exc)}")

    return {'status_code': response.status_code, 'response_json': response_json}


def _output(json):
    return dumps(json, sort_keys=False, indent=4)


def execute_trapi_lookup(case, creator, rbag):
    """

    :param case:
    :param creator:
    :param rbag:
    """
    # Create TRAPI query/response
    rbag.location = case['location']
    rbag.case = case
    trapi_request, output_element, output_node_binding = creator(case)
    if trapi_request is None:
        # The particular creator cannot make a valid message from this triple
        assert False, f"\nCreator method '{creator.__name__}' for test case \n" + \
                      f"\t{_output(case)}\n" + \
                      f"could not generate a valid TRAPI query request object?"

    # query use cases pertain to a particular TRAPI version
    trapi_version = get_trapi_version()

    if not is_valid_trapi(trapi_request, trapi_version=trapi_version):
        # This is a problem with the testing framework.
        assert False, f"execute_trapi_lookup({case['url']}): Invalid TRAPI '{trapi_version}' " + \
                      f"query request {_output(trapi_request)}"

    trapi_response = call_trapi(case['url'], case['query_opts'], trapi_request)

    # Successfully invoked the query endpoint
    rbag.request = trapi_request
    rbag.response = trapi_response

    if trapi_response['status_code'] != 200:
        err_msg = f"execute_trapi_lookup({case['url']}): " + \
                  f"TRAPI request:\n\t{_output(trapi_request)}\n " + \
                  f"returned status code: {str(trapi_response['status_code'])} " + \
                  f"and response:\n\t '{_output(trapi_response['response_json'])}'"
        logger.warning(err_msg)
        assert False, err_msg

    # Validate that we got back valid TRAPI Response
    assert is_valid_trapi(trapi_response['response_json'], trapi_version=trapi_version), \
           f"execute_trapi_lookup({case['url']}): " + \
           f"TRAPI request:\n\t{_output(trapi_request)}\n " + \
           f"had an invalid TRAPI '{trapi_version}' response:\n\t" + \
           f"{_output(trapi_response['response_json'])}"

    response_message = trapi_response['response_json']['message']

    # Verify that the response had some results
    assert len(response_message['results']) > 0, \
           f"execute_trapi_lookup({case['url']}): empty TRAPI Result from TRAPI request:\n\t" + \
           f"{_output(trapi_request)}"

    # The results contained the object of the query
    object_ids = [r['node_bindings'][output_node_binding][0]['id'] for r in response_message['results']]
    assert case[output_element] in object_ids, \
           f"execute_trapi_lookup({case['url']}): TRAPI request:\n\t{_output(trapi_request)}\n " + \
           f"had missing or invalid TRAPI Result object ID bindings in response method results:\n\t" \
           f"{_output(response_message)}"

    return response_message