"""
Translator SmartAPI Registry access module.
"""
from typing import Optional, List, Dict, NamedTuple, Set
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


def validate_test_data_location(url: str) -> Optional[str]:
    """
    Validates the resource file name and internet access of the specified test_data_location, but not file content.

    :param url: original URL value asserted to be the internet resolvable component's test data file
    :return: bool, True if accessible JSON file; False otherwise.
    """
    if not url:
        logger.error(f"validate_test_data_location(): empty URL?")
    elif not url.startswith('http'):
        logger.error(f"validate_test_data_location(): Resource '{url}' is not an internet URL?")
    elif not url.endswith('json'):
        logger.error(f"validate_test_data_location(): JSON Resource '{url}' expected to have a 'json' file extension?")
    else:
        # Sanity check: rewrite 'regular' Github page endpoints to
        # test_data_location JSON files, into 'raw' file endpoints
        # before attempting access to the resource
        url = rewrite_github_url(url)

        try:
            request = requests.get(url)
            if request.status_code == 200:
                # Success! return the successfully accessed
                # (possibly rewritten) test_data_location URL
                return url
            else:
                logger.error(
                    f"validate_test_data_location(): '{url}' access returned http status code: {request.status_code}?"
                )
        except RequestException as re:
            logger.error(f"validate_test_data_location(): exception {str(re)}?")

    # default is to fail here
    return None


class RegistryEntryId(NamedTuple):
    service_title: str
    service_version: str
    trapi_version: str
    biolink_version: str


# here, we track Registry duplications of KP and ARA infores identifiers
_infores_catalog: Dict[str, List[RegistryEntryId]] = dict()

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


def extract_component_test_metadata_from_registry(
        registry_data: Dict,
        component_type: str
) -> Dict[str, Dict[str,  Optional[str]]]:
    """
    Extract metadata from a registry data dictionary, for all components of a specified type.

    :param registry_data:
        Dict, Translator SmartAPI Registry dataset
        from which specific component_type metadata will be extracted.
    :param component_type: str, value 'KP' or 'ARA'
    :return: Dict[str, Dict[str,  Optional[str]]] of metadata, indexed by 'test_data_location'
    """

    # Sanity check...
    assert component_type in ["KP", "ARA"]

    service_metadata: Dict[str, Dict[str, Optional[str]]] = dict()

    for index, service in enumerate(registry_data['hits']):

        # We are only interested in services belonging to a given category of components
        component = tag_value(service, "info.x-translator.component")
        if not (component and component == component_type):
            continue

        service_title = tag_value(service, "info.title")
        if not service_title:
            logger.warning(f"Service {index} lacks a 'service_title'... Skipped?")
            continue

        if 'servers' not in service:
            logger.warning(f"Service {index} lacks a 'servers' block... Skipped?")
            continue
        servers: Optional[List[Dict]] = service['servers']

        infores = tag_value(service, "info.x-translator.infores")
        # Internally, within SRI Testing, we only track the object_id of the infores CURIE
        infores = infores.replace("infores:", "") if infores else None

        if not infores:
            logger.warning(f"Registry {component} entry {service_title} has no 'infores' identifier. Skipping?")
            continue

        if infores in _ignored_resources:
            logger.warning(f"Registry {component} entry with {infores} is tagged to be ignored. Skipping?")
            continue

        raw_test_data_location: Optional[str] = tag_value(service, "info.x-trapi.test_data_location")

        # ... and only interested in resources with a non-empty, valid, accessible test_data_location specified
        test_data_location = validate_test_data_location(raw_test_data_location)
        if not test_data_location:
            logger.warning(
                f"Empty, invalid or inaccessible test data resource '{test_data_location}' " +
                f"for Service {index}: '{service_title}'... Service entry skipped?")
            continue

        # Once past the test_data_location gauntlet, we start
        # to collect the remaining Registry metadata

        # Grab additional service metadata, then store it all
        service_version = tag_value(service, "info.version")
        trapi_version = tag_value(service, "info.x-trapi.version")
        biolink_version = tag_value(service, "info.x-translator.biolink-version")

        # TODO: temporary hack to deal with resources which are somewhat sloppy or erroneous in their declaration
        #       of the applicable Biolink Model version for validation: enforce a minimium Biolink Model version.
        if not biolink_version or SemVer.from_string(MINIMUM_BIOLINK_VERSION) >= SemVer.from_string(biolink_version):
            biolink_version = MINIMUM_BIOLINK_VERSION

        if infores not in _infores_catalog:
            _infores_catalog[infores] = list()
        else:
            logger.warning(
                f"Infores '{infores}' appears duplicated among {component} Registry entries. " +
                f"The new entry reports a service version '{str(service_version)}', " +
                f"TRAPI version '{str(trapi_version)}' and Biolink Version '{str(biolink_version)}'."
            )

        url: Optional[str] = None
        for server in servers:
            # For the time being, we assume that the first 'url' encountered is a sensible testing target
            # TODO: 'x-maturity' may later modify our approach for testing
            if 'url' in server:
                url = server['url']
                break

        if not url:
            logger.warning(f"Service {index} lacks a 'testing' or 'staging' x-maturity endpoint... Skipped?")
            continue

        if test_data_location not in service_metadata:
            service_metadata[test_data_location] = dict()
        else:
            # TODO: duplicate test_data_locations may be problematic for our unique indexing of the service,
            #       Should be rather now be indexing the services by (infores, trapi_version, biolink_version)?
            logger.warning(
                f"Ignoring service {index}: '{service_title}' " +
                f"with a duplicate test_data_location '{test_data_location}'?"
            )
            continue

        entry_id: RegistryEntryId = RegistryEntryId(service_title, service_version, trapi_version, biolink_version)

        _infores_catalog[infores].append(entry_id)

        capture_tag_value(service_metadata, test_data_location, "url", url)
        capture_tag_value(service_metadata, test_data_location, "service_title", service_title)
        capture_tag_value(service_metadata, test_data_location, "service_version", service_version)
        capture_tag_value(service_metadata, test_data_location, "component", component_type)
        capture_tag_value(service_metadata, test_data_location, "infores", infores)
        capture_tag_value(service_metadata, test_data_location, "biolink_version", biolink_version)
        capture_tag_value(service_metadata, test_data_location, "trapi_version", trapi_version)

    return service_metadata


# Singleton reading of the Registry Data
# (do I need to periodically refresh it in long-running applications?)
_the_registry_data: Optional[Dict] = None


def get_the_registry_data():
    global _the_registry_data
    if not _the_registry_data:
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
