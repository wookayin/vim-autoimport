import asyncio
import sys
import itertools
from pathlib import Path

import pytest

try:
    from blessed import Terminal
    term = Terminal()
    YELLOW, GREEN, CYAN = term.yellow, term.green, term.cyan
    NORMAL = term.normal
except:
    YELLOW = GREEN = CYAN = NORMAL = ''


def testPyImport():
    from vim_autoimport.managers.python import PyImport
    assert str(PyImport("tensorflow")) == "import tensorflow"
    assert str(PyImport("tensorflow", alias="tf")) == "import tensorflow as tf"
    assert str(PyImport(package="glob", symbol="glob")) == \
        "from glob import glob"
    assert str(PyImport(package="glob", symbol="glob", alias="glob2")) == \
        "from glob import glob as glob2"
    with pytest.raises(TypeError):
        PyImport(symbol="a")

    assert PyImport("numpy") == PyImport("numpy")  # equality
    assert PyImport("John", "Doe") > PyImport("Jane", "Doe")  # ordering
    assert PyImport("lib", "numpy", "np") > PyImport("lib", "numpy")
    assert PyImport("lib", "numpy", "np") != PyImport("lib", "numpy")
    assert not (PyImport("lib", "numpy", "np") == PyImport("lib", "numpy"))
    assert hash(PyImport("numpy", symbol="linalg", alias="la"))


def testDatabase():
    from vim_autoimport.managers.python import DB, _build_database
    import time

    t0 = time.time()
    _build_database()
    t1 = time.time()

    print("size: %d" % len(DB))
    for k, v in sorted(DB.items()):
        print(YELLOW, "%-30s" % k, NORMAL, " -> ", GREEN, str(v), NORMAL, sep='')
    assert DB

    print("Time for _build_database(): %.3f sec" % (t1 - t0))



# All builtin modules for python3: https://docs.python.org/3/py-modindex.html
with open(Path(__file__).parent.joinpath("../../../test/python_builtins.txt")) as f:
    BUILTIN_MODULES = [l for l in f.read().strip().split('\n')
                       if not l.startswith('#')]


@pytest.mark.timeout(0.5)
def testImportResolveBasic(ctags_fixture):
    from vim_autoimport.managers.python import PythonImportManager
    manager = PythonImportManager()
    print("[testImportResolve]")

    def resolve(symbol):
        r = manager.resolve_import(symbol)
        print(' ', YELLOW, "%-30s" % symbol, NORMAL, " -> ",
              GREEN if r else '', r, NORMAL, sep='')
        return r
    def section(text):
        print(CYAN, text, NORMAL, sep='')

    #==========================================================================
    section("database (+chaining)")
    #==========================================================================
    assert resolve("os.path.exists") == "import os.path"
    assert resolve("np") == "import numpy as np"
    assert resolve("abstractmethod") == "from abc import abstractmethod"
    assert resolve("scipy.misc.face") == "import scipy.misc"
    assert resolve("scipy.stats.t") == "import scipy"
    assert resolve("plt.imshow.__name__") == "import matplotlib.pyplot as plt"
    assert resolve("random.sample") == "import random"

    # built-in modules but not visible from pkgutil
    assert resolve("time.sleep") == "import time"
    assert resolve("gc.collect") == "import gc"

    for b in BUILTIN_MODULES:
        if b.startswith('_'): continue
        # TODO support these exception more nicely.
        if any(b.startswith(v) for v in [
            'dbm', 'distutils', 'email', 'tkinter', 'wsgiref', 'xml']):
            continue   # too many subpackages
        if any(b.startswith(v) for v in ['glob', 'pprint']):
            continue
        if any(b.startswith(v) for v in ['msilib', 'msvcrt', 'winreg', 'winsound']):
            continue  # windows only
        if any(b.startswith(v) for v in ['ossaudiodev', 'pwd', 'spwd']):
            continue  # linux only
        assert resolve(b) == "import {}".format(b), (
            "Did not resolve for the builtin module `{}`".format(b))

    #==========================================================================
    section("pkgutil (+chaining)")
    #==========================================================================
    assert resolve("antigravity") == "import antigravity"  # builtin :)
    assert resolve("vim_autoimport.managers.python.PythonImportManager") \
        == "import vim_autoimport"  # itself?  # TODO import full subpackage

    #==========================================================================
    section("don't know")
    #==========================================================================
    assert resolve("_this_is_unknown") == None
    assert resolve("_unknown.prefix.sys") == None


@pytest.fixture
def ctags_fixture(mocker):
    """A fixture mocking ctags output for SitePackagesCTagsStrategy."""
    from vim_autoimport.managers.python import SitePackagesCTagsStrategy
    async def ctags_mock():
        """full ctags is slow; mock ctags output line by line."""
        yield '!This is a comment line -- should be ignored'
        # valid items
        yield '\t'.join(['MyConstant', 'package1/constants.py', '/^MyConstant = 1', 'v'])
        yield '\t'.join(['SomeClass', 'lib2/models/some_class.py', '/^class SomeClass', 'c'])
        # symbols from test suites should be excluded
        yield '\t'.join(['foo', 'lib2/tests/test_foo.py', '/^def foo()', 'f'])
        yield '\t'.join(['bar', 'lib2/tests/bar_test.py', '/^def bar()', 'f'])
        # duplicates from different modules
        yield '\t'.join(['John', 'names/Lennon.py', '/^class John', 'c'])
        yield '\t'.join(['John', 'names/Doe.py', '/^class John', 'c'])
    def wrap_as_future(obj):
        f = asyncio.Future()
        f.set_result(obj)
        return f
    mocker.patch.object(SitePackagesCTagsStrategy, '_run_ctags',
                        side_effect=lambda: wrap_as_future(ctags_mock()))



@pytest.mark.timeout(1.0)
def testSitePackagesCTags(ctags_fixture, mocker):
    from vim_autoimport.managers.python import SitePackagesCTagsStrategy
    from vim_autoimport.managers.python import PythonImportManager
    manager = PythonImportManager()

    # let's see what is included in the built database
    strategy = [s for s in manager._strategies
                if isinstance(s, SitePackagesCTagsStrategy)][0]
    asyncio.get_event_loop().run_until_complete(strategy._future)

    tags = strategy._tags
    print("Length =", len(tags))
    assert tags, "Tags not built?"
    print("--" * 50)
    for k, v in sorted(tags.items()):
        print(NORMAL, "%-40s" % k, NORMAL, " -> ", YELLOW, str(v), NORMAL, sep='')
    print("--" * 50)

    assert 'SomeClass' in tags
    assert 'some_class.SomeClass' in tags
    assert 'lib2.models.some_class' in tags
    assert 'some_class' in tags

    # now run some import test cases ...
    # ----------------------------------
    def resolve(symbol):
        r = manager.resolve_import(symbol)
        print(' ', YELLOW, "%-40s" % symbol, NORMAL, " -> ",
              GREEN if r else '', r, NORMAL, sep='')
        return r

    assert resolve("MyConstant") is None, "constant should not be indexed"
    assert resolve("SomeClass") == \
        "from lib2.models.some_class import SomeClass"
    assert resolve("some_class") == \
        "from lib2.models import some_class"
    assert resolve("some_class.SomeClass") == \
        "from lib2.models import some_class"
    assert resolve("lib2.models.some_class.SomeClass") == \
        "import lib2.models.some_class"
    assert resolve("lib2.models.some_class.AnotherClass") == \
        "import lib2.models.some_class"
    assert resolve("foo") is None, "test files should not be indexed"
    assert resolve("bar") is None, "test files should not be indexed"

    # duplicated entries: ask user
    import vim_autoimport.vim_utils as vim_utils
    mocker.patch.object(vim_utils, 'ask_user', return_value=1)
    assert resolve("John") == "from names.Doe import John"  # D precedes L


@pytest.mark.timeout(10.0)
@pytest.mark.skipif('not config.getvalue("all")',
                    reason="Do not run slow tests unless --all was specified")
def testSitePackagesCTagsReal():
    from vim_autoimport.managers.python import PythonImportManager
    from vim_autoimport.managers.python import SitePackagesCTagsStrategy
    manager = PythonImportManager()

    strategies = [s for s in manager._strategies
                  if isinstance(s, SitePackagesCTagsStrategy)]
    print("")

    for strategy in strategies:
        # await ctag is done
        asyncio.get_event_loop().run_until_complete(strategy._future)

        tags = strategy._tags
        print(GREEN, "{}, len(tags) = {}".format(
            type(strategy).__name__, len(tags)), NORMAL, sep='')
        for k, v in itertools.islice(tags.items(), 0, 20):
            print(YELLOW, "  %-40s" % k, NORMAL, list(map(str, v)), sep='')
        print(YELLOW, '  ...', NORMAL, sep='')
        assert tags

        # do more check?
        assert '__init__' not in tags, \
            "__init__ should not exist\n:" + "\n".join(str(v) for v in tags['__init__'])


if __name__ == '__main__':
    pytest.main(["-s", "-v"] + sys.argv)
