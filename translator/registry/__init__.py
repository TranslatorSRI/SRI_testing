"""
Translator SmartAPI Registry access module.
"""
from functools import lru_cache
from typing import Optional, Union, List, Dict, NamedTuple, Set, Tuple, Any
from datetime import datetime

import requests
import yaml
from reasoner_validator.versioning import SemVer

from requests.exceptions import RequestException

import logging

from tests.translator.registry import MOCK_REGISTRY, MOCK_TRANSLATOR_SMARTAPI_REGISTRY_METADATA

logger = logging.getLogger(__name__)

SMARTAPI_URL = "https://smart-api.info/api/"
SMARTAPI_QUERY_PARAMETERS = "q=__all__&tags=%22trapi%22&" + \
                            "fields=servers,info,_meta,_status,paths,tags,openapi,swagger&size=1000&from=0"

MINIMUM_BIOLINK_VERSION = "2.2.11"  # use RTX-KG2 as the minimum version


def set_timestamp():
    dtnow = datetime.now()
    # getting the timestamp
    ts = datetime.timestamp(dtnow)
    # convert to datetime
    dt = str(datetime.fromtimestamp(ts))
    return dt.split(".")[0]


def get_spec(spec_url):
    spec = None
    try:
        meta_data = requests.get(spec_url)
        if ".json" in spec_url:
            spec = meta_data.json()
        elif ".yml" in spec_url or ".yaml" in spec_url:
            spec = yaml.safe_load(meta_data.content)
    except Exception as e:
        print(e)
    return spec


def get_status(url, meta_path):
    status = None
    try:
        request = requests.get(url + meta_path)
        status = request.status_code
    except Exception as e:
        print(e)
    return status


def query_smart_api(url: str = SMARTAPI_URL, parameters: Optional[str] = None) -> Optional[Dict]:
    """
    Retrieve Translator SmartAPI Metadata for a specified query parameter filter.

    :param url: str, base URL for Translator SmartAPI Registry
    :param parameters: Optional[str], string of query parameters for Translator SmartAPI Registry
    :return: dict, catalog of Translator SmartAPI Metadata indexed by "test_data_location" source.
    """
    # ... if not faking it, access the real thing...
    query_string = f"query?{parameters}" if parameters else "query"
    data: Optional[Dict] = None
    try:
        if MOCK_REGISTRY:
            # TODO: Using Mock data for now given that the "real" repository
            #       currently lacks KP and ARA 'test_data_location' tags.
            # double deak: fake special "fake URL" unit test result
            if url == "fake URL":
                raise RequestException(f"fake URL!")

            data = MOCK_TRANSLATOR_SMARTAPI_REGISTRY_METADATA

        else:

            request = requests.get(f"{url}{query_string}")
            if request.status_code == 200:
                data = request.json()

    except RequestException as re:
        print(re)
        data = {"Error": "Translator SmartAPI Registry Access Exception: "+str(re)}

    return data


def iterate_services_from_registry(registry_data):
    """

    :param registry_data: Translator SmartAPI Registry catalog (i.e. as returned by query_smart_api())
    :return:
    """
    service_status_data = []
    for index, service in enumerate(registry_data['hits']):
        print(index, service['info']['title'], set_timestamp())
        try:
            service_spec = get_spec(service['_meta']['url'])
            for server in service_spec['servers']:
                source_data_packet = {
                    "title": service['info']['title'],
                    "time_retrieved": set_timestamp(),
                    "component": service['info']['x-translator']['component'],
                    "meta_data_url": service['_meta']['url'],
                    "server_url": server['url'],
                    "server_x_maturity": None,
                    "server_status": None,
                }
                if 'x-maturity' in server.keys():
                    source_data_packet['server_x_maturity'] = server['x-maturity']
                service_paths = [x for x in service['paths'] if 'meta' in x]
                meta_kg_path = service_paths[0]
                source_data_packet['server_status'] = get_status(server['url'], meta_kg_path)
                print(server['url'], meta_kg_path, source_data_packet['server_status'])
                service_status_data.append(source_data_packet)
        except Exception as e:
            print(e)
    return service_status_data


def get_nested_tag_value(data: Dict, path: List[str], pos: int) -> Optional[str]:
    """
    Navigate dot delimited tag 'path' into a multi-level dictionary, to return its associated value.

    :param data: Dict, multi-level data dictionary
    :param path: str, dotted JSON tag path
    :param pos: int, zero-based current position in tag path
    :return: string value of the multi-level tag, if available; 'None' otherwise if no tag value found in the path
    """
    tag = path[pos]
    part_tag_path = ".".join(path[:pos+1])
    if tag not in data:
        logger.debug(f"\tMissing tag path '{part_tag_path}'?")
        return None

    pos += 1
    if pos == len(path):
        return data[tag]
    else:
        return get_nested_tag_value(data[tag], path, pos)


def tag_value(json_data, tag_path) -> Optional[str]:
    """

    :param json_data:
    :param tag_path:
    :return:
    """
    if not tag_path:
        logger.debug(f"\tEmpty 'tag_path' argument?")
        return None

    parts = tag_path.split(".")
    return get_nested_tag_value(json_data, parts, 0)


def capture_tag_value(service_metadata: Dict, resource: str, tag: str, value: str):
    """

    :param service_metadata:
    :param resource:
    :param tag:
    :param value:
    """
    if value:
        logger.info(f"\t{resource} '{tag}': {value}")
        service_metadata[resource][tag] = value
    else:
        logger.warning(f"\t{resource} is missing its service '{tag}'")
        service_metadata[resource][tag] = None


def rewrite_github_url(url: str) -> str:
    """
    If the URL is a regular Github page specification of a file, then rewrite
    the URL to point to the corresponding https://raw.githubusercontent.com.
    Non-Github URLs and raw.githubusercontent.com URLs themselves are simply returned unaltered.

    :param url: input url
    :return:
    """
    if not url:
        logger.warning("rewrite_github_url(): URL is empty?")
        return ""
    if url.startswith("https://github.com"):
        logger.info(f"rewrite_github_url(): rewriting '{url}' to raw github link?")
        url = url.replace("https://github.com", "https://raw.githubusercontent.com")
        url = url.replace("/blob", "", 1)
    return url


@lru_cache(maxsize=1024)
def validate_url(url: str) -> Optional[str]:
    # Simple URL string to validate
    if not url.startswith('http'):
        logger.error(
            f"validate_url(): Simple string test_data_location " +
            f"'{url}' is not a valid URL?"
        )
    #
    # As it happens, Translator teams are not fastidious about using .json file
    # extensions to their test data, so we relax this constraint on test data files.
    #
    # elif not url.endswith('json'):
    #     logger.error(f"validate_url(): JSON Resource " +
    #                  f"'{url}' expected to have a 'json' file extension?")
    else:
        # Sanity check: rewrite 'regular' Github page endpoints to
        # test_data_location JSON files, into 'raw' file endpoints
        # before attempting access to the resource
        test_data_location = rewrite_github_url(url)

        try:
            request = requests.get(test_data_location)
            if request.status_code == 200:
                # Success! return the successfully accessed
                # (possibly rewritten) test_data_location URL
                return test_data_location
            else:
                logger.error(
                    f"validate_url(): '{test_data_location}' access " +
                    f"returned http status code: {request.status_code}?"
                )
        except RequestException as re:
            logger.error(f"validate_url(): exception {str(re)}?")

    return None


def _select_url(urls: Optional[Union[str, List, Dict]]) -> Optional[str]:
    simple_raw_url: Optional[str] = None
    if urls:
        if isinstance(urls, str):
            simple_raw_url = urls
        elif isinstance(urls, List):
            # This is most often incorrect since it may ignore
            # most of the test data, but it won't crash the system
            simple_raw_url = urls[0]

    # A regular Git URL's may need to be
    # rewritten to a 'raw' Git file access REST url
    return rewrite_github_url(simple_raw_url) if simple_raw_url else None


def get_default_url(test_data_location: Optional[Union[str, List, Dict]]) -> Optional[str]:
    """
    This method selects a default test_data_location url for use in test data / configuration retrieval.

    This is an temporary heuristic solution for the SRI Testing framework to work around complexity in the new
    info.x-trapi.test_data_location data model, with its x-maturity indexed, possible multiple, test data sources.

    :param test_data_location: Optional[Union[str, List, Dict]]
    :return: a single resolved URL to a REST JSON file - KP test data or ARA test configuration; None if not available
    """
    resolved_url: Optional[str] = _select_url(test_data_location)
    if resolved_url:
        return resolved_url
    elif isinstance(test_data_location, Dict):
        urls: Optional[Union[str, List[str]]] = None
        # assume an x_maturity precedence order
        for x_maturity in ['default', 'production', 'staging', 'testing', 'development']:
            if x_maturity in test_data_location:
                urls = test_data_location[x_maturity]
                break
        return _select_url(urls)
    else:
        # fall through failure
        return None


def parse_test_urls(test_data_location) -> Optional[Union[str, List[str]]]:

    if isinstance(test_data_location, str):
        # 'classical' simple string URL value
        return validate_url(test_data_location)

    elif isinstance(test_data_location, List):
        # List of URL strings
        url_list: List[str] = list()
        for location in test_data_location:
            url: Optional[str] = validate_url(location)
            if url:
                url_list.append(url)
        if url_list:
            return url_list

    # Fall through value is failure
    return None


def parse_test_environment_urls(test_environments: Dict) -> Optional[Dict]:
    """
    Parses 'full' Translator SmartAPI Registry entry info.x-trapi.test_data_location property specification
    (option 2 format discussed in https://github.com/TranslatorSRI/SRI_testing/issues/59#issuecomment-1275136793).

    :param test_environments: Dict, complex specification of test_data_location (see schema)
    :return: Optional[Dict], an x-maturity indexed URL catalog (including 'default' values)
    """
    valid_urls: Dict = dict()
    for x_maturity in test_environments.keys():
        if x_maturity not in {'default', 'production', 'staging', 'testing', 'development'}:
            logger.warning(f"Unknown x-maturity value: {x_maturity}")
        else:
            test_url_object = test_environments[x_maturity]
            if isinstance(test_url_object, Dict) and 'url' in test_url_object:
                urls: Optional[Union[str, List[str]]] = parse_test_urls(test_url_object['url'])
                if urls:
                    valid_urls[x_maturity] = urls
                    continue

            logger.warning(f"Invalid test_url_object: '{test_url_object}'")

    return valid_urls


def validate_test_data_locations(
        test_data_location: Optional[Union[str, List, Dict]]
) -> Optional[Union[str, List, Dict]]:
    """
    Parses the contents of the test_data_location but not (yet) the REST file to which the test data location points.

    :param test_data_location: original URL value asserted to specify an REST resolvable file
    :return: Optional[Union[str, List, Dict]], single string URL, array of URL's or an x-maturity indexed URL catalog
    """
    try:
        if not test_data_location:
            logger.error(f"validate_test_data_locations(): empty URL?")
            return None

        elif isinstance(test_data_location, Dict):
            # Parse in an instance of the new extended JSON object data model for info.x-trapi.test_data_location.
            # See https://github.com/NCATSTranslator/translator_extensions/pull/19/files for the applicable schema.
            x_maturity_urls: Dict = parse_test_environment_urls(test_data_location)
            if x_maturity_urls:
                return x_maturity_urls
        else:
            # simpler url specification
            urls: Optional[Union[str, List[str]]] = parse_test_urls(test_data_location)
            if urls:
                return urls

        raise RuntimeError("Valid test_data_location values not found?")

    except RuntimeError:
        return None


class RegistryEntryId(NamedTuple):
    service_title: str
    service_version: str
    trapi_version: str
    biolink_version: str


# here, we track Registry duplications of KP and ARA services
_service_catalog: Dict[str, List[RegistryEntryId]] = dict()

# Some ARA's and KP's may be tagged tp be ignored for practical reasons
_ignored_resources: Set[str] = {
    "empty",
    # "rtx-kg2",  # the test_data_location released for RTX-KG2 is relatively unusable, as of September 2022
    # "molepro",  # TODO: temporarily skip MolePro...
    # "arax",     # temporarily skip ARAX ARA
    # "sri-reference-kg",
    # "automat-icees-kg",
    # "cohd",
    # "service-provider-trapi",
}


@lru_cache(maxsize=1024)
def live_trapi_endpoint(url: str) -> bool:
    """
    Checks if TRAPI endpoint is accessible.
    Current implementation performs a GET on the
    TRAPI /meta_knowledge_graph endpoint,
    to verify that a resource is 'alive'

    :param url: str, URL of TRAPI endpoint to be checked
    :return: bool, True if endpoint is 'alive'; False otherwise
    """
    if not url:
        return False

    # We test TRAPI endpoints by a simple 'GET'
    # to its '/meta_knowledge_graph' endpoint
    mkg_test_url: str = f"{url}/meta_knowledge_graph"
    try:
        request = requests.get(mkg_test_url)
        if request.status_code == 200:
            # Success! given url is deemed a 'live' TRAPI endpoint
            return True
        else:
            logger.error(
                f"live_trapi_endpoint(): TRAPI endpoint '{url}' is inaccessible? " +
                f"Returned http status code: {request.status_code}?"
            )
    except RequestException as re:
        logger.error(f"live_trapi_endpoint(): requests.get() exception {str(re)}?")

    return False


def select_endpoint(
        server_urls: Dict[str, List[str]],
        test_data_location: Optional[Union[str, List, Dict]],
        check_access: bool = True
) -> Optional[Tuple[str, str, Union[str, List[str]]]]:
    """
    Select one test URL based on available server_urls and test_data_location specification. Usually, by the time
    this method is called, any 'x_maturity' preference has constrained the server_urls. The expectation at this point
    is that the chosen 'x_maturity' also has test data available, either in specific to the 'x_maturity' or 'default'.
    Failing that, if the server_urls have several x_maturity environments, the highest precedence x_maturity which has
    test data available (possibly 'default' in origin) is taken. The precedence is in order of: 'production', 'staging',
    'testing' and 'development' (this could change in the future, based on Translator community deliberations...).
    If the server_urls and test_data_location specifications don't overlap, then "None" is returned.

    :param server_urls: Dict, the indexed catalog of available Translator SmartAPI Registry entry 'servers' block urls
    :param test_data_location: Optional[Union[str, List, Dict]], info.x-trapi.test_data_location specification
    :param check_access: bool, verify TRAPI access of endpoints before returning (Default: True)

    :return: Optional[Tuple[str, str, Union[str, List]]], selected URL endpoint, 'x-maturity' tag and
                                                          associated test data reference: single URL or list of URLs
    """
    # Check the possible target testing environments
    # in an ad hoc hardcoded of the 'precedence/rank'
    # ordering of the DEPLOYMENT_TYPES list
    urls: Optional[List[str]] = None
    x_maturity: Optional[str] = None
    test_data: Optional[Union[str, List[str]]] = None
    for environment in DEPLOYMENT_TYPES:
        if environment in server_urls:
            # If available, filter environments against 'x-maturity'
            # tagged 'test_data_location' values targeted for testing
            if isinstance(test_data_location, Dict):
                if environment not in test_data_location:
                    continue

                # Otherwise,  'test_data_location' specification is
                # available for the given x-maturity key and
                # successfully matched one of the selected 'x-maturity',
                # one of the DEPLOYMENT_TYPES or the 'default' url?
                test_data = test_data_location[environment]
            else:
                # Otherwise, the test_data_location is a simple string or list of strings thus
                # no discrimination in the test_data_location(s) concerning target
                # 'x-maturity' thus, we just return the 'highest ranked'
                # x-maturity server endpoint found in the servers block
                test_data = test_data_location

            urls = server_urls[environment]
            x_maturity = environment
            break

    if not urls and isinstance(test_data_location, Dict) and 'default' in test_data_location:
        # The first time around, we couldn't align with an *explicitly*
        # equivalent x-maturity object-model specified test data location.
        # So we repeat the ordered search for available x-maturity endpoints,
        # now using any suitable 'default' test data set which is available
        for environment in DEPLOYMENT_TYPES:
            if environment in server_urls:
                urls = server_urls[environment]
                x_maturity = environment
                test_data = test_data_location['default']
                break

    # ... Now, resolve one of the available endpoints
    url: Optional[str] = None
    if urls:
        for endpoint in urls:
            if not check_access or live_trapi_endpoint(endpoint):
                # Since they are all deemed 'functionally equivalent' by the Translator team, the first
                # 'live' endpoint, within the given x-maturity set, is selected as usable for testing.
                url = endpoint
                break

    if url:
        # Selected endpoint, if successfully resolved
        return url, x_maturity, test_data
    else:
        return None


def validate_servers(
        infores: str,
        service: Dict,
        x_maturity: Optional[str] = None
) -> Optional[Dict[str, List[str]]]:
    """
    Validate the servers block, returning it or None if unavailable.

    :param infores: str, InfoRes reference id of the service
    :param service: Dict, service metadata (from Registry)
    :param x_maturity: Optional[str], target x-maturity (if set; may be None if not unconstrained)
    :return: Dict, catalog of x-maturity environment servers; None if unavailable.
    """
    servers: Optional[List[Dict]] = service['servers']

    if not servers:
        logger.warning(f"Registry entry '{infores}' missing a 'servers' block? Skipping...")
        return None

    server_urls: Dict = dict()
    for server in servers:
        if not (
                'url' in server and
                'x-maturity' in server and
                server['x-maturity'] in DEPLOYMENT_TYPES
        ):
            # sanity check!
            continue

        environment = server['x-maturity']

        # Design decisions emerging out of 29 November 2022 Translator Architecture meeting:

        # 1. Check here for explicitly specified 'x_maturity'; otherwise, iterate to select...
        if x_maturity and environment != x_maturity.lower():
            continue

        # 2. Discussions confirmed that if multiple x-maturity urls are present, then they are all
        #    'functionally identical'; however, they may not all be operational.  We will thus now  keep a list of
        #    such endpoints around then iterate through then when issuing TRAPI calls, in case that some are offline?
        env_endpoint = server['url']
        if environment not in server_urls:
            # first url seen for a given for a given x-maturity
            server_urls[environment] = list()

        logger.info(
            f"Registry entry '{infores}' x-maturity '{environment}' includes  url '{env_endpoint}'."
        )
        server_urls[environment].append(env_endpoint)

    return server_urls


def get_testable_resource(
        index: int,
        service: Dict
) -> Optional[Tuple[str, List[str]]]:
    """
    Validates a service as testable and resolves then returns parameters for testing.

    :param index: int, internal sequence number (i.e. hit number in the Translator SmartAPI Registry)
    :param service: Dict, indexed metadata about a component service (from the Registry)
    :return: Optional[Tuple[str, List[str]]], composed of the infores reference id and
             List of associated 'testable' x_maturities; None if unavailable
    """
    infores = tag_value(service, "info.x-translator.infores")
    if not infores:
        logger.warning(f"Registry entry '{index}' has no 'infores' identifier. Skipping?")
        return None
    else:
        # Internally, within SRI Testing, we only track the object_id of the infores CURIE
        infores = infores.replace("infores:", "")

    if not ('servers' in service and service['servers']):
        logger.warning(f"Registry '{index}' entry '{infores}' lacks a 'servers' block... Skipped?")
        return None

    raw_test_data_location: Optional[Union[str, Dict]] = tag_value(service, "info.x-trapi.test_data_location")

    # ... and only interested in resources with a non-empty, valid, accessible test_data_location specified
    test_data_location: Optional[Union[str, List, Dict]] = validate_test_data_locations(raw_test_data_location)
    if not test_data_location:
        logger.warning(
            f"Empty, invalid or inaccessible 'info.x-trapi.test_data_location' specification "
            f"'{str(raw_test_data_location)}' for Registry '{index}' entry  '{infores}'! Untestable service skipped?")
        return None

    is_default: bool = False
    if isinstance(test_data_location, str) or isinstance(test_data_location, List):
        is_default = True
    else:
        if 'default' in test_data_location:
            is_default = True

    server_urls: Dict = validate_servers(infores=infores, service=service)

    # By the time we are here, we either have a one selected
    # x_maturity environments or None (if a specific x_maturity was set) or,
    # if no such x_maturity preference, a catalog of (possibly one selected)
    # available 'x_maturity' environments from which to select for testing.
    # We filter out the latter situation first...
    if not server_urls:
        return None

    x_maturities: List[str] = list()

    if is_default:
        # if there is a default, then all servers are deemed
        # testable even if they may have specific test data
        x_maturities = list(server_urls.keys())
    else:
        # Otherwise, find intersection set between server_urls and test_data_location x-maturities
        for x_maturity in server_urls.keys():
            if x_maturity in test_data_location:
                x_maturities.append(x_maturity)

    if x_maturities:
        return infores, x_maturities
    else:
        # no intersecting set of servers and
        # test_data_location x_maturities?
        return None


def validate_testable_resource(
        index: int,
        service: Dict,
        component: str,
        x_maturity: Optional[str] = None
) -> Optional[Dict[str, Union[str, List]]]:
    """
    Validates a service as testable and resolves then returns parameters for testing.

    :param index: int, internal sequence number (i.e. hit number in the Translator SmartAPI Registry)
    :param service: Dict, indexed metadata about a component service (from the Registry)
    :param component: str, type of component, one of 'KP' or 'ARA'
    :param x_maturity: Optional[str], 'x_maturity' environment target for test run (system chooses if not specified)
    :return: augmented resource metadata for a given KP or ARA service confirmed to be 'testable'
             for one selected x-maturity environment; None if unavailable
    """
    #
    # This 'overloaded' function actually checks a number of parameters that need to be present for testable resources.
    # If the validation of all parameters succeeds, it returns a dictionary of those values; otherwise, returns 'None'
    #
    resource_metadata: Dict = dict()

    service_title = tag_value(service, "info.title")
    if service_title:
        resource_metadata['service_title'] = service_title
    else:
        logger.warning(f"Registry {component} entry '{str(index)}' lacks a 'service_title'... Skipped?")
        return None

    if not ('servers' in service and service['servers']):
        logger.warning(f"Registry {component} entry '{service_title}' lacks a 'servers' block... Skipped?")
        return None

    infores = tag_value(service, "info.x-translator.infores")

    # Internally, within SRI Testing, we only track the object_id of the infores CURIE
    infores = infores.replace("infores:", "") if infores else None

    if infores:
        resource_metadata['infores'] = infores
    else:
        logger.warning(f"Registry entry '{infores}' has no 'infores' identifier. Skipping?")
        return None

    if infores in _ignored_resources:
        logger.warning(
            f"Registry entry '{infores}' is tagged to be ignored. Skipping?"
        )
        return None

    raw_test_data_location: Optional[Union[str, Dict]] = tag_value(service, "info.x-trapi.test_data_location")

    # ... and only interested in resources with a non-empty, valid, accessible test_data_location specified
    test_data_location: Optional[Union[str, List, Dict]] = validate_test_data_locations(raw_test_data_location)
    if test_data_location:
        # Optional[Union[str, List, Dict]], may be a single URL string, an array of URL string's,
        # or an x-maturity indexed catalog of URLs (single or List of URL string(s))
        resource_metadata['test_data_location'] = test_data_location
    else:
        logger.warning(
            f"Empty, invalid or inaccessible 'info.x-trapi.test_data_location' specification "
            f"'{str(raw_test_data_location)}' for Registry entry '{infores}'! Service entry skipped?")
        return None

    servers: Optional[List[Dict]] = service['servers']

    if not servers:
        logger.warning(f"Registry entry '{infores}' missing a 'servers' block? Skipping...")
        return None

    server_urls: Dict = validate_servers(infores=infores, service=service, x_maturity=x_maturity)

    # By the time we are here, we either have a one selected
    # x_maturity environments or None (if a specific x_maturity was set) or,
    # if no such x_maturity preference, a catalog of (possibly one selected)
    # available 'x_maturity' environments from which to select for testing.

    # We filter out the latter situation first...
    if not server_urls:
        return None

    # Now, we try to select one of the endpoints for testing
    testable_system: Optional[Tuple[str, str, Union[str, List[str]]]] = \
        select_endpoint(server_urls, test_data_location)

    if testable_system:
        url: str
        x_maturity: str
        test_data: Union[str, List]
        url, x_maturity, test_data = testable_system
        resource_metadata['url'] = url
        resource_metadata['x_maturity'] = x_maturity
        if isinstance(test_data, List):
            resource_metadata['test_data_location'] = test_data
        else:
            resource_metadata['test_data_location'] = [test_data]
    else:
        # not likely, but another sanity check!
        logger.warning(f"Service {str(index)} has incomplete testable system parameters... Skipped?")
        return None

    # Resource Metadata returned with 'testable' endpoint, tagged
    # with by x-maturity and associated with suitable test data
    # (single or list of test data file url strings)
    return resource_metadata


def get_testable_resources_from_registry(
        registry_data: Dict
) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """
    Simpler version of the extract_component_test_metadata_from_registry() method,
    that only returns the InfoRes reference identifiers of all testable resources.

    :param registry_data:
        Dict, Translator SmartAPI Registry dataset
        from which specific component_type metadata will be extracted.

    :return: 2-Tuple(Dict[str, List[str]], Dict[str, List[str]]) dictionaries with keys
             of the reference id's of InfoRes CURIES of available KPs and ARAs, with
            value list of associated x-maturity environments available for testing.
    """

    kp_ids: Dict[str, List[str]] = dict()
    ara_ids: Dict[str, List[str]] = dict()

    for index, service in enumerate(registry_data['hits']):

        # We are only interested in services belonging to a given category of components
        component = tag_value(service, "info.x-translator.component")
        if not (component and component in ["KP", "ARA"]):
            continue

        resource: Optional[Tuple[str, List[str]]] = get_testable_resource(index, service)

        if not resource:
            continue

        infores: str = resource[0]

        if component == "KP":

            if infores not in kp_ids:
                kp_ids[infores] = list()

            kp_ids[infores].extend(resource[1])

        elif component == "ARA":

            if infores not in ara_ids:
                ara_ids[infores] = list()

            ara_ids[infores].extend(resource[1])

    return kp_ids, ara_ids


def source_of_interest(service: Dict, target_sources: Set[str]) -> Optional[str]:
    """
    Source filtering function, checking a source identifier against a set of identifiers.
    The target_source strings may also be wildcard patterns with a single asterix (only)
    with possible prefix only, suffix only or prefix-<body>-suffix matches.

    :param service: Dict, Translator SmartAPI Registry entry for one service 'hit' containing an 'infores' property
    :param target_sources: Set[str], of target identifiers or wildcard patterns of interest against which to filter service infores reference identifiers
    :return: Optional[str], infores if matched; None otherwise.
    """
    assert service, "registry.source_of_interest() method call: unexpected empty service?!?"

    infores = tag_value(service, "info.x-translator.infores")

    # Internally, within SRI Testing, we only track the object_id of the infores CURIE
    infores = infores.replace("infores:", "") if infores else None

    if not infores:
        service_title = tag_value(service, "info.title")
        logger.warning(f"Registry entry for '{str(service_title)}' has no 'infores' identifier. Skipping?")
        return None

    if target_sources:
        found: bool = False
        for entry in target_sources:

            if entry.find("*") >= 0:
                part = entry.split(sep="*", maxsplit=1)  # part should be a 2-tuple
                if not part[0] or infores.startswith(part[0]):
                    if not part[1] or infores.endswith(part[1]):
                        found = True
                        break

            elif infores == entry:  # exact match?
                found = True
                break

        if not found:
            return None

    # default if no target_sources or matching
    return infores


# TODO: this is an ordered list giving 'production' testing priority
#       but not sure about preferred testing priority.
#       See https://github.com/TranslatorSRI/SRI_testing/issues/61 and also
#           https://github.com/TranslatorSRI/SRI_testing/issues/59
DEPLOYMENT_TYPES: List[str] = ['production', 'staging', 'testing', 'development']


def extract_component_test_metadata_from_registry(
        registry_data: Dict,
        component_type: str,
        source: Optional[str] = None,
        x_maturity: Optional[str] = None
) -> Dict[str, Dict[str, Optional[Union[str, Dict]]]]:
    """
    Extract metadata from a registry data dictionary, for all components of a specified type.

    :param registry_data:
        Dict, Translator SmartAPI Registry dataset
        from which specific component_type metadata will be extracted.
    :param component_type: str, value 'KP' or 'ARA'
    :param source: Optional[str], ara_id or kp_id(s) source(s) of test configuration data in the registry.
                                  Return 'all' resources of the given component type if the source is None.
                                  The 'source' may be a scalar string, or a comma-delimited set of strings.
                                  If the 'source' string includes a single asterix ('*'), it is treated
                                  as a wildcard match to the infores name being filtered.
                                  Note that all identifiers here should be the reference (object) id's
                                  of the Infores CURIE of the target resource.
    :param x_maturity: Optional[str], x_maturity environment target for test run (system chooses if not specified)

    :return: Dict[str, Dict[str,  Optional[str]]] of metadata, indexed by 'test_data_location'
    """

    # Sanity check...
    assert component_type in ["KP", "ARA"]

    # TODO: is there a way to translate target_sources into a compiled
    #       regex pattern, for more efficient screening of infores (below)?
    #       Or pre-process the target_sources into a list of 2-tuple patterns to match?
    target_sources: Set[str] = set()
    if source:
        # if specified, 'source' may be a comma separated list of
        # (possibly wild card pattern matching) source strings...
        for infores in source.split(","):
            infores = infores.strip()
            target_sources.add(infores)

    service_metadata: Dict[str, Dict[str, Optional[Union[str, Dict]]]] = dict()

    for index, service in enumerate(registry_data['hits']):

        # We are only interested in services belonging to a given category of components
        component = tag_value(service, "info.x-translator.component")
        if not (component and component == component_type):
            continue

        # Filter on target sources of interest
        infores: Optional[str] = source_of_interest(service=service, target_sources=target_sources)
        if not infores:
            # silently ignore any resource whose InfoRes CURIE
            # reference identifier is missing or doesn't have a partial
            # of exact match to a specified non-empty target source
            continue

        resource_metadata: Optional[Dict[str, Any]] = \
            validate_testable_resource(index, service, component, x_maturity)
        if not resource_metadata:
            continue

        # Once past the 'testable resources' metadata gauntlet,
        # the following parameters are assumed valid and non-empty
        service_title: str = resource_metadata['service_title']

        # this 'url' is the service endpoint in the
        # specified 'x_maturity' environment
        url: str = resource_metadata['url']
        x_maturity: str = resource_metadata['x_maturity']

        # The 'test_data_location' also has url's but these are now expressed
        # in a polymorphic manner: Optional[Dict[str, Union[str, List, Dict]]].
        # See validate_test_data_locations above for details
        test_data_location = resource_metadata['test_data_location']

        # Now, we start to collect the remaining Registry metadata

        # Grab additional service metadata, then store it all
        service_version = tag_value(service, "info.version")
        trapi_version = tag_value(service, "info.x-trapi.version")
        biolink_version = tag_value(service, "info.x-translator.biolink-version")

        # TODO: temporary hack to deal with resources which are somewhat sloppy or erroneous in their declaration
        #       of the applicable Biolink Model version for validation: enforce a minimium Biolink Model version.
        if not biolink_version or SemVer.from_string(MINIMUM_BIOLINK_VERSION) >= SemVer.from_string(biolink_version):
            biolink_version = MINIMUM_BIOLINK_VERSION

        # Index services by (infores, trapi_version, biolink_version)
        service_id: str = f"{infores},{trapi_version},{biolink_version}"

        if service_id not in _service_catalog:
            _service_catalog[service_id] = list()
        else:
            logger.warning(
                f"Infores '{infores}' appears duplicated among {component} Registry entries. " +
                f"The new entry reports a service version '{str(service_version)}', " +
                f"TRAPI version '{str(trapi_version)}' and Biolink Version '{str(biolink_version)}'."
            )

        if service_id not in service_metadata:
            service_metadata[service_id] = dict()
        else:
            logger.warning(
                f"Ignoring service {index}: '{service_title}' with a duplicate service" +
                f"'infores,trapi_version,biolink_version' identifier: '{service_id}'?"
            )
            continue

        entry_id: RegistryEntryId = RegistryEntryId(service_title, service_version, trapi_version, biolink_version)

        _service_catalog[service_id].append(entry_id)

        capture_tag_value(service_metadata, service_id, "url", url)
        capture_tag_value(service_metadata, service_id, "x_maturity", x_maturity)
        capture_tag_value(service_metadata, service_id, "service_title", service_title)
        capture_tag_value(service_metadata, service_id, "service_version", service_version)
        capture_tag_value(service_metadata, service_id, "component", component_type)
        capture_tag_value(service_metadata, service_id, "infores", infores)
        capture_tag_value(service_metadata, service_id, "test_data_location", test_data_location)
        capture_tag_value(service_metadata, service_id, "biolink_version", biolink_version)
        capture_tag_value(service_metadata, service_id, "trapi_version", trapi_version)

    return service_metadata


# Singleton reading of the Registry Data
# (do I need to periodically refresh it in long-running applications?)
_the_registry_data: Optional[Dict] = None


def get_the_registry_data(refresh: bool = False):
    global _the_registry_data
    if not _the_registry_data or refresh:
        _the_registry_data = query_smart_api(parameters=SMARTAPI_QUERY_PARAMETERS)
    return _the_registry_data


def get_remote_test_data_file(url: str) -> Optional[Dict]:
    """

    :param url: URL of SRI test data file template for a given resource
    :return: dictionary of test data parameters
    """
    data: Optional[Dict] = None
    try:
        request = requests.get(f"{url}")
        if request.status_code == 200:
            data = request.json()
    except RequestException as re:
        print(re)
        data = {"Error": f"Translator component test data file '{url}' cannot be accessed: "+str(re)}

    return data
