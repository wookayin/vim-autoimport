"""vim_autoimport.managers.python"""

from typing import List, Optional
from collections import namedtuple
import pkgutil

import vim

from .manager import AutoImportManager, LineNumber


class PythonImportManager(AutoImportManager):
    """A import manager for Python.

    Currently it only lookups a pre-defined database for resolving imports,
    but could be smarter being aware of LSP, ctags, regexp-based importable
    symbols from site-packages or the current project tree, etc.
    """

    def __init__(self):
        if not DB:
            _build_database()   # TODO: Add thread lock.

    def resolve_import(self, symbol: str) -> Optional[str]:
        # p.a.c.k.a.g.e.symbol -> if any ancestor package is known, import it
        def _ancestor_packages(symbol_chain):
            chain = symbol_chain.split('.')
            for k in range(1, len(chain)):
                yield '.'.join(chain[:-k])

        # TODO: Implement ResolveStrategy classes for smarter resolution chain.
        # (1) lookup the database as-is
        if symbol in DB:
            return next(iter((DB[symbol])))
        for parent_package in _ancestor_packages(symbol):
            if parent_package in DB:
                return next(iter((DB[parent_package])))

        # (2) pkgutil.iter_modules: get importable modules
        importable_modules: List[str] = [
            module_info.name for module_info in pkgutil.iter_modules()
            if module_info.ispkg]

        if symbol in importable_modules:
            return 'import {}'.format(symbol)
        for parent_package in _ancestor_packages(symbol):
            if parent_package in importable_modules:
                return 'import {}'.format(parent_package)

        return None

    def is_import_statement(self, line: str):
        line = line.strip()
        if '\n' in line:
            return False
        return line.startswith('from ') or line.startswith('import ')

    AVOID_SYNGROUPS = set(
        ['pythonString', 'pythonDocstring', 'pythonComment']
    )

    def determine_linenumber(self, import_statement: str) -> LineNumber:
        # TODO: Find a correct place for import,
        # being aware of docstrings, import statements, etc.
        buf = vim.current.buffer

        ln: LineNumber
        for ln, bline in enumerate(buf, start=LineNumber(1)):
            if ln > 100: break  # do not scan too many lines

            if bline == '':
                continue
            if self.get_syngroup_at_line(ln) in self.AVOID_SYNGROUPS:
                continue
            return ln

        # cannot resolve, put in the topmost line
        return 1


# -----------------------------------------------------------------------------
# Commonsense database of python imports, determined by the current python
# TODO: Make this list configurable and overridable by users.

import collections, importlib, fnmatch
DB = collections.defaultdict(list)   # symbol -> import statement

ALL = lambda pkg: importlib.import_module(pkg).__all__
DIR = lambda pkg: [s for s in dir(importlib.import_module(pkg))
                   if not s.startswith('_')]
def PATTERN(*pats):
    return (lambda pkg: [s for s in ALL(pkg) if
                         any(fnmatch.fnmatch(s, pat) for pat in pats)])

# common builtin modules: export (selective) symbols that are quite obvious
# so could be imported directly (e.g. `from typing import Any`).
# @see https://docs.python.org/3/py-modindex.html
DB_MODULES_BUILTIN = {
    'sys': None, 'os': None, 'os.path': None,
    're': None, 'math': None, 'random': None,
    'abc': ['ABC', 'ABCMeta', 'abstractclassmethod', 'abstractmethod',
            'abstractproperty', 'abstractstaticmethod'],
    'argparse': PATTERN('Argument*', '*Formatter'),
    'collections': ALL,
    'contextlib': ['contextmanager', 'nullcontext', 'closing'],
    'copy': ['deepcopy'],
    'enum': ['Enum', 'EnumMeta', 'Flag', 'IntEnum', 'IntFlag'],
    'functools': ALL,
    'glob': ['glob', 'iglob'],
    'importlib': ALL,
    'io': PATTERN('*IO*', 'Buffered*'),
    'itertools': DIR,
    'pathlib': ALL,
    'pprint': ALL,
    'typing': lambda pkg: filter(lambda s: s[0].isupper(), ALL(pkg))
}

DB_MODULES_IMPORT = ['numpy', 'scipy', 'scipy.misc', 'matplotlib']
DB_MODULES_IMPORT_AS = {
    'numpy': 'np', 'pandas': 'pd',
    'matplotlib.pyplot': 'plt', 'matplotlib': 'mpl',
}

def _build_database():
    for pkg, symbols in DB_MODULES_BUILTIN.items():
        if callable(symbols):
            try:
                symbols = symbols(pkg)
            except ImportError:
                symbols = None
        for s in (symbols or []):
            DB[s].append('from {} import {}'.format(pkg, s))
        DB[pkg].append('import ' + pkg)

    for s in DB_MODULES_IMPORT:
        DB[s].append('import ' + s)
    for pkg, s in DB_MODULES_IMPORT_AS.items():
        DB[s].append('import {} as {}'.format(pkg, s))
    return DB
