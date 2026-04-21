import json
import os
import sys
import unittest
from collections import defaultdict

# '''
# Add the src directory to path so that imports will work
# this assumes that the src directory is adjacent to this file
# '''
# FILE_PATH = os.path.dirname(os.path.abspath(__file__))
# SRC_PATH = r"C:\Users\David\Documents\Teaching\CS518\2026-01-spring\guide-finder\src"

TEST_PATH = r"/home/owen/Desktop/CS518/cs-518-group/tests"

# SRC_DIR = os.path.join(SRC_PATH)#, 'src')
# sys.path.append(SRC_DIR)

def build_test_hierarchy(test_item, hierarchy=None):
    if hierarchy is None:
        # Structure: { module: { class: [methods] } }
        hierarchy = defaultdict(lambda: defaultdict(list))

    if isinstance(test_item, unittest.TestSuite):
        for test in test_item:
            build_test_hierarchy(test, hierarchy)
    else:
        module = test_item.__class__.__module__
        classname = test_item.__class__.__name__
        method = getattr(test_item, '_testMethodName', 'UnknownMethod')
        
        # Append the method to the nested dict
        if method not in hierarchy[module][classname]:
            hierarchy[module][classname].append(method)
            
    return hierarchy

def discover_tests(directory, dump, details=True):
    """
    Discovers all tests in a given directory and runs them.

    Args:
        directory (str): The path to the directory containing test files.
    """
    # Ensure the provided directory exists and is a directory
    if not os.path.isdir(directory):
        print(f"Error: The directory '{directory}' does not exist.")
        sys.exit(1)

    # Use TestLoader.discover() to find all tests
    # The 'start_dir' is the directory to start searching from.
    # The 'pattern' is the file name pattern to match for test files.
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover(start_dir=directory, pattern='test_*.py')

    # Usage Example:
    # suite = unittest.TestLoader().discover('tests')
    structured_data = build_test_hierarchy(test_suite)

    # To print it beautifully:
    with open(dump, 'w') as json_file:
        json.dump(structured_data, json_file, indent=4)

if __name__ == '__main__':

    sd = discover_tests(TEST_PATH, dump='tests.json')

