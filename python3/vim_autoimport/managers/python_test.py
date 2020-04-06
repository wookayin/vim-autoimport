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
    from vim_autoimport.managers.python import DB
    print("")
    for k, v in DB.items():
        print(YELLOW, "%-30s" % k, NORMAL, " -> ", GREEN, str(v), NORMAL, sep='')


if __name__ == '__main__':
    pytest.main()
