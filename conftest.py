# During unit test, the vim module might not be present.
# Therefore we should mock vim module before importing any packages.
import sys
sys.modules['vim'] = type(sys)('vim')


def pytest_addoption(parser):
    parser.addoption("--all", action="store_true", help="run slow tests")
