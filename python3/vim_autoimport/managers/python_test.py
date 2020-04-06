import sys
import pytest

# mock vim module
sys.modules['vim'] = type(sys)('vim')

try:
    from blessed import Terminal
    term = Terminal()
    YELLOW, GREEN, NORMAL = term.yellow, term.green, term.normal
except:
    YELLOW = GREEN, NORMAL = ''


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


if __name__ == '__main__':
    pytest.main()
