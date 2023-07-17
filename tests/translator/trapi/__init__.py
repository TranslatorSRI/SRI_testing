from sys import stderr
from os import sep
from os.path import dirname, abspath

TRAPI_TEST_DIRECTORY = abspath(dirname(__file__))
print(f"TRAPI Test Directory: {TRAPI_TEST_DIRECTORY}", file=stderr)

PATCHED_140_SCHEMA_FILEPATH = f"{TRAPI_TEST_DIRECTORY}{sep}test_trapi_1.4.0-beta5.yaml"
