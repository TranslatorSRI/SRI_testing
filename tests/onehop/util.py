from copy import deepcopy
from dataclasses import asdict
from functools import wraps
from typing import Set, Dict, List, Tuple, Optional

from bmt import utils
from reasoner_validator.versioning import SemVer
from reasoner_validator.biolink import get_biolink_model_toolkit
from sri_testing.translator.sri.testing.util import ontology_kp


def create_one_hop_message(edge, look_up_subject: bool = False) -> Tuple[Optional[Dict], str]:
    """Given a complete edge, create a valid TRAPI message for "one hop" querying for the edge.
    If the look_up_subject is False (default) then the object id is not included, (lookup object
    by subject) and if the look_up_subject is True, then the subject id is not included (look up
    subject by object)"""
    trapi_version_tested = SemVer.from_string(edge['trapi_version'])
    if trapi_version_tested <= SemVer.from_string("1.1.0"):
        return None, f"Legacy TRAPI version '{str(edge['trapi_version'])}' unsupported by SRI Testing!"

    query_graph: Dict = {
        "nodes": {
            'a': {
                "categories": [edge['subject_category']]
            },
            'b': {
                "categories": [edge['object_category']]
            }
        },
        "edges": {
            'ab': {
                "subject": "a",
                "object": "b",
                "predicates": [edge['predicate']]
            }
        }
    }
    if look_up_subject:
        query_graph['nodes']['b']['ids'] = [edge['object']]
    else:
        query_graph['nodes']['a']['ids'] = [edge['subject']]
    message: Dict = {
        "message": {
            "query_graph": query_graph,
            'knowledge_graph': {
                "nodes": {}, "edges": {},
            },
            'results': []
        }
    }
    return message, ""


#####################################################################################################
#
# Functions for creating TRAPI messages from a known edge
#
# Each function returns the new message, and also some information used to evaluate whether the
# correct value was retrieved.  The second return value (object or subject) is the name of what is
# being returned and the third value (a or b) is which query node it should be bound to in one of the
# results.  For example, when we look up a triple by subject, we should expect that the object entity
# is bound to query node b.
#
#####################################################################################################
# Available Unit Tests:
#
# - by_subject
# - inverse_by_new_subject
# - by_object
# - raise_subject_entity
# - raise_object_entity
# - raise_object_by_subject
# - raise_predicate_by_subject
#
#####################################################################################################
_unit_tests: Dict = dict()
_unit_test_definitions: Dict = dict()


def get_unit_test_definitions() -> Dict:
    return _unit_test_definitions.copy()


def get_unit_test_codes() -> Set[str]:
    global _unit_tests
    return set(_unit_tests.keys())


def get_unit_test_name(code: str) -> str:
    global _unit_tests
    return _unit_tests[code]


def get_unit_test_list() -> List[str]:
    global _unit_tests
    return list(_unit_tests.values())


def in_excluded_tests(test, test_case) -> bool:
    global _unit_tests
    try:
        test_name = test.__name__
    except AttributeError:
        raise RuntimeError(f"in_excluded_tests(): invalid 'test' parameter: '{str(test)}'")
    try:
        if "exclude_tests" in test_case:
            # returns 'true' if the test_name corresponds to a test in the list of excluded test (codes)
            return any([test_name == get_unit_test_name(code) for code in test_case["exclude_tests"]])
    except TypeError as te:
        raise RuntimeError(f"in_excluded_tests(): invalid 'test_case' parameter: '{str(test_case)}': {str(te)}")
    except KeyError as ke:
        raise RuntimeError(
            f"in_excluded_tests(): invalid test_case['excluded_test'] code? " +
            f"'{str(test_case['excluded_tests'])}': {str(ke)}"
        )

    return False


class TestCode:
    """
    Assigns a shorthand test code to a unit test method.
    """
    def __init__(self, code: str, unit_test_name: str, description: str):
        global _unit_tests
        self.code = code
        self.method = unit_test_name
        _unit_tests[code] = unit_test_name
        _unit_test_definitions[unit_test_name] = description

    def __call__(self, fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)
            return result
        return wrapper


@TestCode(
    code="BS",
    unit_test_name="by_subject",
    description="Given a known triple, create a TRAPI message that looks up the object by the subject"
)
def by_subject(request):
    """
    :param request: test case with test edge data used to construct unit test TRAPI query.
    :return: Tuple, (trapi_request, output_element, output_node_binding);
             if trapi_request is None, then error details returned in two other tuple elements
    """
    message, errmsg = create_one_hop_message(request)
    if message:
        return message, 'object', 'b'
    else:
        return None, f"by_subject|subject '{str(request['subject'])}'", errmsg


@TestCode(
    code="IBNS",
    unit_test_name="inverse_by_new_subject",
    description="Given a known triple, create a TRAPI message that inverts the predicate, " +
                "then looks up the new object by the new subject (original object)"
)
def inverse_by_new_subject(request):
    """
    :param request: test case with test edge data used to construct unit test TRAPI query.
    :return: Tuple, (trapi_request, output_element, output_node_binding);
             if trapi_request is None, then error details returned in two other tuple elements
    """
    tk = get_biolink_model_toolkit(biolink_version=request['biolink_version'])
    context: str = f"inverse_by_new_subject|predicate '{str(request['predicate'])}')"
    original_predicate_element = tk.get_element(request['predicate'])
    if not original_predicate_element:
        reason: str = "is an unknown element?"
        return None, context, reason
    elif original_predicate_element['symmetric']:
        transformed_predicate = request['predicate']
    else:
        transformed_predicate_name = tk.get_inverse(original_predicate_element.name)
        if transformed_predicate_name is None:
            transformed_predicate = None
        else:
            tp = tk.get_element(transformed_predicate_name)
            transformed_predicate = utils.format_element(tp)

    # Not everything has an inverse (it should, and it will, but it doesn't right now)
    if transformed_predicate is None:
        reason: str = "does not have an inverse?"
        return None, context, reason

    # probably don't need to worry here but just-in-case
    # only work off a copy of the original request...
    transformed_request = request.copy()
    transformed_request.update({
        "subject_category": request['object_category'],
        "object_category": request['subject_category'],
        "predicate": transformed_predicate,
        "subject": request['object'],
        "object": request['subject']
    })
    message, errmsg = create_one_hop_message(transformed_request)
    # We inverted the predicate, and will be querying by the new subject, so the output will be in node b
    # but, the entity we are looking for (now the object) was originally the subject because of the inversion.
    if message:
        return message, 'subject', 'b'
    else:
        return None, context, errmsg


@TestCode(
    code="BO",
    unit_test_name="by_object",
    description="Given a known triple, create a TRAPI message that looks up the subject by the object"
)
def by_object(request):
    """
    :param request: test case with test edge data used to construct unit test TRAPI query.
    :return: Tuple, (trapi_request, output_element, output_node_binding);
             if trapi_request is None, then error details returned in two other tuple elements
    """
    message, errmsg = create_one_hop_message(request, look_up_subject=True)
    if message:
        return message, 'subject', 'a'
    else:
        return None, f"by_object|object '{str(request['object'])}'", errmsg


def no_parent_error(unit_test_name: str, element: Dict, suffix: Optional[str] = None) -> Tuple[None, str, str]:
    context: str = f"{unit_test_name}|element '{str(element['name'])}'"
    reason: str = "has no 'is_a' parent"
    if 'mixin' in element and element['mixin']:
        reason += " and is a mixin"
    if 'abstract' in element and element['abstract']:
        reason += " and is abstract"
    if 'deprecated' in element and element['deprecated']:
        reason += " and is deprecated"
    if suffix:
        reason += suffix
    return None, context, reason


def raise_entity(request, target: str):
    """
    Generic method - parameterized by association edge node target (either "subject" or "object") -
    that, given a known triple, creates a TRAPI message that uses a parent instance of the original entity
    to query for its association partner node. This only works if a given entity id namespace is listed in
    the 'id_prefix' list of the entity category and specifies some kind of hierarchical ontology of terms"

    :param request: test case edge data
    :param target: target context for ontological 'raising': either "subject" or "object"
    :return:
    """
    # Sanity check!
    assert target in ["subject", "object"]

    category = request[f"{target}_category"]
    entity = request[target]
    parent_entity = ontology_kp.get_parent(entity, category, biolink_version=request['biolink_version'])
    if parent_entity is None:
        return no_parent_error(
            f"raise_{target}_entity",
            {'name': f"{entity}[{category}]"},
            suffix=" since it is either not an ontology term or does not map onto a parent ontology term."
        )
    mod_request = deepcopy(request)
    mod_request[target] = parent_entity
    message, errmsg = create_one_hop_message(mod_request)
    if message:
        # query the opposing association node partner here
        return message, "subject" if target == "object" else "object", 'a'
    else:
        return None, f"raise_{target}_entity|parent entity '{str(parent_entity)}'", errmsg


@TestCode(
    code="RSE",
    unit_test_name="raise_subject_entity",
    description="Given a known triple, creates a TRAPI message that uses a parent instance of the original subject " +
                "to query for its object node. This only works if a given subject entity id namespace is listed " +
                "in the 'id_prefix' list of the category and specifies some kind of hierarchical ontology of terms."
)
def raise_subject_entity(request):
    """
    :param request: test case with test edge data used to construct unit test TRAPI query.
    :return: Tuple, (trapi_request, output_element, output_node_binding);
             if trapi_request is None, then error details returned in two other tuple elements
    """
    return raise_entity(request, "subject")


@TestCode(
    code="ROE",
    unit_test_name="raise_object_entity",
    description="Given a known triple, creates a TRAPI message that uses a parent instance of the original object " +
                "to query for its subject node. This only works if a given object entity id namespace is listed " +
                "in the 'id_prefix' list of the category and specifies some kind of hierarchical ontology of terms."
)
def raise_object_entity(request):
    """
    :param request: test case with test edge data used to construct unit test TRAPI query.
    :return: Tuple, (trapi_request, output_element, output_node_binding);
             if trapi_request is None, then error details returned in two other tuple elements
    """
    return raise_entity(request, "object")


@TestCode(
    code="ROBS",
    unit_test_name="raise_object_by_subject",
    description="Given a known triple, create a TRAPI message that uses the parent " +
                "of the original object category and looks up the object by the subject"
)
def raise_object_by_subject(request):
    """
    :param request: test case with test edge data used to construct unit test TRAPI query.
    :return: Tuple, (trapi_request, output_element, output_node_binding);
             if trapi_request is None, then error details returned in two other tuple elements
    """
    tk = get_biolink_model_toolkit(biolink_version=request['biolink_version'])
    original_object_element = tk.get_element(request['object_category'])
    if original_object_element:
        original_object_element = asdict(original_object_element)
    else:
        original_object_element = dict()
        original_object_element['name'] = request['object_category']
        original_object_element['is_a'] = None
    if original_object_element['is_a'] is None:
        # This element may be a mixin or abstract, without any parent?
        return no_parent_error(f"raise_object_by_subject", original_object_element)
    transformed_request = request.copy()  # there's no depth to request, so it's ok
    parent = tk.get_parent(original_object_element['name'])
    transformed_request['object_category'] = utils.format_element(tk.get_element(parent))
    message, errmsg = create_one_hop_message(transformed_request)
    if message:
        return message, 'object', 'b'
    else:
        return None, f"raise_object_by_subject|object_category '{str(request['object_category'])}'", errmsg


@TestCode(
    code="RPBS",
    unit_test_name="raise_predicate_by_subject",
    description="Given a known triple, create a TRAPI message that uses the parent " +
                "of the original predicate and looks up the object by the subject"
)
def raise_predicate_by_subject(request):
    """
    :param request: test case with test edge data used to construct unit test TRAPI query.
    :return: Tuple, (trapi_request, output_element, output_node_binding);
             if trapi_request is None, then error details returned in two other tuple elements
    """
    tk = get_biolink_model_toolkit(biolink_version=request['biolink_version'])
    transformed_request = request.copy()  # there's no depth to request, so it's ok
    if request['predicate'] != 'biolink:related_to':
        original_predicate_element = tk.get_element(request['predicate'])
        if original_predicate_element:
            original_predicate_element = asdict(original_predicate_element)
        else:
            original_predicate_element = dict()
            original_predicate_element['name'] = request['predicate']
            original_predicate_element['is_a'] = None
        if original_predicate_element['is_a'] is None:
            # This element may be a mixin or abstract, without any parent?
            return no_parent_error("raise_predicate_by_subject", original_predicate_element)
        parent = tk.get_parent(original_predicate_element['name'])
        transformed_request['predicate'] = utils.format_element(tk.get_element(parent))
    message, errmsg = create_one_hop_message(transformed_request)
    if message:
        return message, 'object', 'b'
    else:
        return None, f"raise_predicate_by_subject|predicate '{str(request['predicate'])}'", errmsg
