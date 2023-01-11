"""
Deprecated - tests relating to the direct parsing of the Pytest output.

Test SRI Testing reporting code snippets
"""
from typing import Optional, Union, Dict, Tuple, Set, List, Any
from os import linesep, path
from json import dumps

import pytest

from translator.sri.testing.util.legacy_test_report import (
    SUMMARY_ENTRY_TAGS,
    SHORT_TEST_SUMMARY_INFO_HEADER_PATTERN,
    PASSED_SKIPPED_FAILED_PATTERN,
    PERCENTAGE_COMPLETION_SUFFIX_PATTERN,
    PYTEST_SUMMARY_PATTERN,
    TEST_CASE_IDENTIFIER_PATTERN,
    SRITestReport,
    PYTEST_HEADER_START_PATTERN,
    PYTEST_HEADER_END_PATTERN,
    PYTEST_FAILURES_START_PATTERN,
    LOGGER_PATTERN,
)
from tests import TEST_DATA_DIR, TEST_RESULT_DIR
from tests.translator.registry import MOCK_TRANSLATOR_SMARTAPI_REGISTRY_METADATA


def mock_pytest_setup():
    # need to fake a few Pytest preconditions
    # (i.e. which would normally be set in the conftest.py)
    mock_resources: List[Dict[str, Any]] = list()
    mock_hits: List[Dict] = MOCK_TRANSLATOR_SMARTAPI_REGISTRY_METADATA["hits"]
    for hit in mock_hits:
        hit_info = hit['info']
        x_translator = hit_info['x-translator']
        x_trapi = hit_info['x-trapi']
        source = x_trapi['test_data_location']
        api_name: str = source.split('/')[-1]
        # remove the trailing file extension
        api_name = api_name.replace(".json", "")
        mock_resources.append(
            {
                "title": hit_info['title'],
                "api_name": api_name,
                "api_version": hit_info['version'],
                "component": x_translator['component'],
                "infores": x_translator['infores'],
                "team": x_translator['team'],
                "biolink_version": x_translator['biolink-version'],
                "trapi_version": x_trapi['version'],
                "test_data_location": x_trapi['test_data_location']
            }
        )

    mock_edge = {
        "subject_category": "PANTHER.FAMILY:PTHR34921:SF1:biolink:GeneFamily",
        "object_category": "PANTHER.FAMILY:PTHR34921:SF1:biolink:GeneFamily",
        "predicate": "biolink:part_of",
        "subject_id": "PANTHER.FAMILY:PTHR34921",
        "object_id": "PANTHER.FAMILY:PTHR34921"
    }
    for metadata in mock_resources:
        cache_resource_metadata(metadata=metadata)
        resource_id = metadata['api_name']
        for edge_idx in range(0, 6):
            edge: Dict = mock_edge.copy()
            edge["idx"] = edge_idx
            add_kp_edge(resource_id, edge_idx, edge)


def test_pytest_header_start_pattern():
    assert PYTEST_HEADER_START_PATTERN.search(
        "============================= test session starts ============================="
    )


@pytest.mark.parametrize(
    "query",
    [
        "collecting ... collected 88 items",
        "collected 88 items",
        " collected 88 items",
        "collected 88 items ",
        " collected 88 items ",
        "collected 88 items\n",
    ]
)
def test_pytest_header_end_pattern(query):
    assert PYTEST_HEADER_END_PATTERN.search(query)


@pytest.mark.parametrize(
    "query",
    [
        "CRITICAL    sometest.py:123 blah, blah, blah",
        "ERROR    sometest.py:123 blah, blah, blah",
        "WARNING    sometest.py:123 blah, blah, blah",
        "INFO    sometest.py:123 blah, blah, blah",
        "DEBUG    sometest.py:123 blah, blah, blah",
        "-------------------------------- live log call --------------------------------"
    ]
)
def test_pytest_logger_pattern(query):
    assert LOGGER_PATTERN.match(query)


TEST_HEADER = """
============================= test session starts =============================

platform win32 -- Python 3.9.7, pytest-7.1.1, pluggy-1.0.0 -- c:\\\\users\\sri_testing\\py\\scripts\\python.exe

cachedir: .pytest_cache

rootdir: C:\\\\SRI_testing\\tests\\onehop

plugins: anyio-3.5.0, asyncio-0.18.2, harvest-1.10.3

asyncio: mode=legacy

collecting ... collected 88 items



test_onehops.py::test_trapi_kps[Test_KP_1#0-by_subject] PASSED           [  1%]
"""


def test_skip_header():
    lines = TEST_HEADER.split('\n')
    line: str
    report: SRITestReport = SRITestReport()
    for line in lines:

        line = line.strip()  # spurious leading and trailing whitespace removed
        if not line:
            continue  # ignore blank lines

        if report.skip_header(line):
            continue

        # if it makes it this far, then this line will be seen?
        assert line == "test_onehops.py::test_trapi_kps[Test_KP_1#0-by_subject] PASSED           [  1%]"


def test_pytest_failures_start_pattern():
    assert PYTEST_FAILURES_START_PATTERN.search(
        "=================================== FAILURES ==================================="
    )


TEST_FAILURES = """================================== FAILURES ===================================
C:\\SRI_testing\\translator\\trapi\\__init__.py:282: AssertionError: test_onehops.py::test_trapi_kps[Test_KP_1#0-by_subject] FAILED  for expected TRAPI version '1.0.0'
C:\\SRI_testing\\translator\\trapi\\__init__.py:282: AssertionError: test_onehops.py::test_trapi_kps[Test_KP_1#0-inverse_by_new_subject] FAILED  for expected TRAPI version '1.0.0'
============================== warnings summary ===============================
Beyond FAILURES"""


def test_annotate_failures():
    lines = TEST_FAILURES.split("\n")
    line: str
    failures_parsed: bool = False
    report: SRITestReport = SRITestReport()
    for line in lines:
        rewritten_line = report.annotate_failures(line)
        if not rewritten_line:
            # We toggle the parse state based on the realization
            # that the rewritten line ought to be blank twice:
            # once at the start and once at the end of the section
            failures_parsed = not failures_parsed
            continue
        if failures_parsed:
            assert rewritten_line.startswith("test_onehops.py::test_trapi_kps")
        else:
            assert rewritten_line == "Beyond FAILURES"


@pytest.mark.parametrize(
    "query",
    [
        f"=========================== short test summary info ============================{linesep}",
        f"===================== short test summary info ============================{linesep}",
        f"=========================== short test summary info ================================={linesep}",
        f"== short test summary info =={linesep}",
        f"{linesep}== short test summary info =={linesep}"
    ]
)
def test_stsi_header_pattern_search(query):
    assert SHORT_TEST_SUMMARY_INFO_HEADER_PATTERN.search(query)


def test_stsi_header_pattern_splitting():
    query = f"Pytest report prefix{linesep}== short test summary info =={linesep}Pytest Report Suffix"
    part = SHORT_TEST_SUMMARY_INFO_HEADER_PATTERN.split(query)
    assert len(part) == 2
    assert part[0] == f"Pytest report prefix{linesep}"
    assert part[1] == f"{linesep}Pytest Report Suffix"


@pytest.mark.parametrize(
    "query",
    [
        (
            "Some_KP#0-by_subject",
            "Some_KP",
            "0",
            "by_subject"
        ),
        (
            "Some_KP#0",
            "Some_KP",
            "0",
            None
        ),
        (
            "Some_KP",
            "Some_KP",
            None,
            None
        ),
        (
            "Some-KP#0-by_subject",
            "Some-KP",
            "0",
            "by_subject"
        ),
        (
            "Test_ARA|Test_KP#1-raise_subject_entity",
            "Test_ARA|Test_KP",
            "1",
            "raise_subject_entity"
        ),
        (
            "Test_ARA|Test_KP#1",
            "Test_ARA|Test_KP",
            "1",
            None
        ),
        (
            "Test_ARA|Test_KP",
            "Test_ARA|Test_KP",
            None,
            None
        ),
        (
            "Test_ARA",
            "Test_ARA",
            None,
            None
        )
    ]
)
def test_case_identifier_pattern(query):
    m = TEST_CASE_IDENTIFIER_PATTERN.search(query[0])
    assert m
    assert m["resource_id"] == query[1]
    assert m["edge_num"] == query[2]
    assert m["test_id"] == query[3]


@pytest.mark.parametrize(
    "query",
    [
        (
                "Test_ARA|Test_KP#2-raise_subject_entity",
                "Test_ARA|Test_KP",
                2,
                "raise_subject_entity"
        ),
        (
                "Test_KP#3-raise_subject_entity",
                "Test_KP",
                3,
                "raise_subject_entity"
        )
    ]
)
def test_parse_case_pattern(query):
    resource_id, edge_num, test_id = SRITestReport.parse_test_case_identifier(query[0])
    assert resource_id == query[1]
    assert edge_num == query[2]
    assert test_id == query[3]


_SAMPLE_BIOLINK_ERRORS = [
    "BLM Version 1.8.2 Error in Knowledge Graph: 'biolink:SmallMolecule' for node " +
    "'PUBCHEM.COMPOUND:597' is not a recognized Biolink Model category?",

    "BLM Version 2.2.16 Error in Knowledge Graph: Edge 'NCBIGene:29974--biolink:interacts_with->" +
    "PUBCHEM.COMPOUND:597' has missing or empty attributes?"
]


@pytest.mark.parametrize(
    "query",
    [
        (  # Query 0 - FAILED KP error message with percentage
            "test_onehops.py::test_trapi_kps[Test_KP_1#4-by_subject] SKIPPED " +
            "(" +
            "test case S-P-O triple '(FOO:1234|biolink:GeneFamily)--[biolink:part_of]" +
            "->(PANTHER.FAMILY:PTHR34921|biolink:GeneFamily)', since it is not Biolink Model compliant" +
            ")" +
            " [ 1%]",
            "SKIPPED",
            "kp",
            "Test_KP_1#4-by_subject",
            "(test case S-P-O triple '(FOO:1234|biolink:GeneFamily)--[biolink:part_of]" +
            "->(PANTHER.FAMILY:PTHR34921|biolink:GeneFamily)', since it is not Biolink Model compliant) [ 1%]",
            "1"
        ),
        (   # New Query 1 - FAILED KP error message with percentage
            "test_onehops.py::test_trapi_kps[Test_KP#0-by_subject] FAILED [  5%]",
            "FAILED",
            "kp",
            "Test_KP#0-by_subject",
            "[  5%]",  # descriptive 'tail' is only the percent completion annotation
            "5"
        ),
        (   # New Query 2 - PASSED KP error message with percentage
            "test_onehops.py::test_trapi_kps[Test_KP_1#0-inverse_by_new_subject] PASSED [ 10%]",
            "PASSED",
            "kp",
            "Test_KP_1#0-inverse_by_new_subject",
            "[ 10%]",  # descriptive 'tail' is only the percent completion annotation
            "10"
        ),
        (   # New Query 3 - FAILED ARA error message with percentage
            "test_onehops.py::test_trapi_aras[Test_ARA|Test_KP#0-by_subject] FAILED    [100%]",
            "FAILED",
            "ara",
            "Test_ARA|Test_KP#0-by_subject",
            "[100%]",  # descriptive 'tail' is only the percent completion annotation
            "100"
        ),
        (   # New Query 4 - FAILED ARA error message without percentage completion
            "test_onehops.py::test_trapi_aras[Test_ARA|Test_KP#0-by_subject] FAILED",
            "FAILED",
            "ara",
            "Test_ARA|Test_KP#0-by_subject",
            None,  # no descriptive 'tail' to the error message
            None   # No percentage completion
        )
    ]
)
def test_passed_skipped_failed_pattern_match(query):
    pskp = PASSED_SKIPPED_FAILED_PATTERN.match(query[0])
    assert pskp
    if query[1]:
        assert pskp["outcome"]
        assert pskp["outcome"] in ["PASSED", "SKIPPED", "FAILED"]
        assert pskp["outcome"] == query[1]
    else:
        assert not pskp["outcome"]

    if query[2]:
        assert pskp["component"]
        assert pskp["component"] in ["kp", "ara"]
        assert pskp["component"] == query[2]
    else:
        assert not pskp["component"]

    if query[3]:
        assert pskp["case"]
        assert pskp["case"] == query[3]
    else:
        assert not pskp["component"]

    tail = pskp["tail"]
    if query[4]:
        assert tail
        assert tail == query[4]
        pcsp = PERCENTAGE_COMPLETION_SUFFIX_PATTERN.search(tail)
        if query[5]:
            assert pcsp
            assert pcsp["percent_complete"] == query[5]
        else:
            assert not pcsp["percent_complete"]
    else:
        assert not tail


TPS = "test_pytest_summary():"


@pytest.mark.parametrize(
    "query",
    [
        ("============= 9 failed, 40 passed, 2 skipped, 4 warning in 83.33s (0:01:23) ==============", 9, 40, 2, 4),
        ("============= 9 failed, 2 skipped, 4 warning in 83.33s (0:01:23) ==============", 9, None, 2, 4),
        ("============= 40 passed, 2 skipped, 4 warning in 83.33s (0:01:23) ==============", None, 40, 2, 4),
        ("============= 9 failed, 40 passed, 4 warning in 83.33s (0:01:23) ==============", 9, 40, None, 4),
        ("============= 9 failed, 40 passed, 2 skipped in 83.33s (0:01:23) ==============", 9, 40, 2, None)
    ]
)
def test_pytest_summary(query):
    match = PYTEST_SUMMARY_PATTERN.match(query[0])
    assert match, f"{TPS} no match?"

    if query[1]:
        assert match["failed"], f"{TPS} 'failed' field not matched?"
        assert match["failed"] == '9', f"{TPS} 'failed' value not matched?"
    if query[2]:
        assert match["passed"], f"{TPS} 'passed' field not matched?"
        assert match["passed"] == '40', f"{TPS} 'passed' value not matched?"
    if query[3]:
        assert match["skipped"], f"{TPS} 'skipped' field not matched?"
        assert match["skipped"] == '2', f"{TPS} 'skipped' field not matched?"
    if query[4]:
        assert match["warning"], f"{TPS} 'warning' field not matched?"
        assert match["warning"] == '4', f"{TPS} 'warning' field not matched?"


TEST_COMPONENT: Dict[str, Set] = {
    "KP": {"Test_KP_1", "Test_KP_2"},
    "ARA": {"Test_ARA|Test_KP_1", "Test_ARA|Test_KP_2"}
}

EDGE_ENTRY_TAGS: Tuple = (
    "subject_category",
    "object_category",
    "predicate",
    "subject",
    "object",
    "tests"
)


@pytest.mark.parametrize(
    "query",
    [
        (
                "sample_pytest_report_1",
                "FAILED",
                True,
                True,
                "6", "19", "63"
        ),
        (
                "sample_pytest_report_2",
                "PASSED",
                True,
                True,
                "11", "14", "63"
        )
    ]
)
def test_parse_test_output(query):
    mock_pytest_setup()
    sample_file_path = path.join(TEST_DATA_DIR, f"{query[0]}.txt")
    report: SRITestReport = SRITestReport()
    with open(sample_file_path, "r") as sf:
        raw_result = sf.read()

        # The function assumes that you are
        # processing the file as a monolithic text blob
        report.parse_result(raw_result)

    output: Optional[Union[str, Dict]] = report.output()
    assert output

    # Top level tags of report
    assert "KP" in output
    assert "ARA" in output
    assert "SUMMARY" in output

    # Core resources from report
    for component in ["KP", "ARA"]:
        for resource_id in TEST_COMPONENT[component]:

            if resource_id not in output[component]:
                print(f"Resource {resource_id} not seen in {component} output? Ignoring...")
                continue

            edges = output[component][resource_id]

            # edges are only reported if FAILED or SKIPPED, not PASSED?
            assert (len(edges) > 0) is query[2 if component == "KP" else 3]

            edge: Dict
            for edge in edges:
                assert all([tag in edge for tag in EDGE_ENTRY_TAGS])
                tests = edge["tests"]
                for test in tests:
                    result: Dict = tests[test]
                    for outcome in result.keys():
                        assert outcome in SUMMARY_ENTRY_TAGS
                        # TODO: can we validate anything further here?

        assert all([tag in output["SUMMARY"] for tag in SUMMARY_ENTRY_TAGS])
        for i, outcome in enumerate(SUMMARY_ENTRY_TAGS):
            assert output["SUMMARY"][outcome] == query[i+4]

    sample_output_path = path.join(TEST_RESULT_DIR, f"{query[0]}.json")
    with open(sample_output_path, "w") as so:
        so.write(dumps(output, indent=4))
