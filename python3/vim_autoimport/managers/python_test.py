import sys
import pytest

# mock vim module
sys.modules['vim'] = type(sys)('vim')

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

    section("database (+chaining)")
    assert resolve("os.path.exists") == "import os.path"
    assert resolve("np") == "import numpy as np"
    assert resolve("abstractmethod") == "from abc import abstractmethod"
    assert resolve("scipy.misc.face") == "import scipy.misc"
    assert resolve("scipy.stats.t") == "import scipy"
    assert resolve("plt.imshow.__name__") == "import matplotlib.pyplot as plt"
    assert resolve("random.sample") == "import random"

    section("pkgutil (+chaining)")
    assert resolve("antigravity") == "import antigravity"  # builtin :)
    assert resolve("vim_autoimport.managers.python.PythonImportManager") \
        == "import vim_autoimport"  # itself?  # TODO import full subpackage

    # Don't know
    section("don't know")
    assert resolve("_this_is_unknown") == None
    assert resolve("_unknown.prefix.sys") == None


if __name__ == '__main__':
    pytest.main(["-s", "-v"] + sys.argv)
