"""
One Hop Test Harness
"""
from sys import stderr
from os.path import dirname, abspath

ONEHOP_TEST_DIRECTORY = abspath(dirname(__file__))
print(f"OneHop Test Directory: {ONEHOP_TEST_DIRECTORY}", file=stderr)
