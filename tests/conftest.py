# tests/conftest.py
# Add the project directory to the Python path
import sys
import os

parent_path = os.path.abspath("..")
tests_path = os.path.abspath(os.path.dirname(__file__))
package_path = os.path.dirname(tests_path)
package_parent_path = os.path.dirname(package_path)

paths = set((parent_path, tests_path, package_path, package_parent_path))

for path in sorted(paths, key=len, reverse=True):
    # print(path)
    sys.path.insert(0, path)
