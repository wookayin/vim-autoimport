import sys
from pathlib import Path
import pytest

try:
    from blessed import Terminal
    term = Terminal()
    YELLOW, GREEN, CYAN = term.yellow, term.green, term.cyan
    NORMAL = term.normal
except:
    YELLOW = GREEN = CYAN = NORMAL = ''


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

@pytest.mark.timeout(1.0)
def testImportResolve():
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


if __name__ == '__main__':
    pytest.main(["-s", "-v"] + sys.argv)
