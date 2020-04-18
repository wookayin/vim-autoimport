"""vim_autoimport.managers.python"""

import abc
from typing import Type, List, Optional
from collections import namedtuple
import pkgutil

import vim

from .utils import funcref
from .manager import AutoImportManager, LineNumber


ImportStatement = str


class PythonImportResolveStrategy(abc.ABC):
    """Strategy interface for AutoImportManager.resolve_import(). All instances
    of its subclasses will be instantiated at each call of resolve_import()."""

    @abc.abstractmethod
    def __call__(self, symbol: str) -> Optional[ImportStatement]:
        del symbol
        raise NotImplementedError


class PythonImportManager(AutoImportManager):
    """A import manager for Python.

    Currently it only lookups a pre-defined database for resolving imports,
    but could be smarter being aware of LSP, ctags, regexp-based importable
    symbols from site-packages or the current project tree, etc.
    """

    def __init__(self):
        if not DB:
            _build_database()   # TODO: Add thread lock.

    def create_strategies(self) -> List[PythonImportResolveStrategy]:
        return [
            DBLookupStrategy(),
            ImportableModuleStrategy(),
        ]

    def resolve_import(self, symbol: str) -> Optional[str]:
        strategies = self.create_strategies()

        # p.a.c.k.a.g.e.symbol -> if any ancestor package is known, import it
        def _ancestor_packages(symbol_chain: str):
            yield symbol_chain  # itself first

            chain = symbol_chain.split('.')
            for k in range(1, len(chain)):
                yield '.'.join(chain[:-k])

        # apply candidates (symbol itself and its all ancestors),
        # and if any match is found by a strategy return it
        for candidate_symbol in _ancestor_packages(symbol):
            for strategy in strategies:
                r: Optional[ImportStatement]
                r = strategy(candidate_symbol)
                if r:
                    return str(r)
        return None

    def is_import_statement(self, line: str) -> bool:
        line = line.strip()
        if '\n' in line:
            return False
        return line.startswith('from ') or line.startswith('import ')

    AVOID_SYNGROUPS = set(
        ['pythonString', 'pythonDocstring', 'pythonComment']
    )

    def determine_linenumber(self, import_statement: str) -> LineNumber:
        # If there is another import statement for the same package as the
        # given one, place nearby the import statement.
        # Otherwise, find the first non-empty, non-comment line and place there.
        buf = vim.current.buffer
        ln: LineNumber
        max_lines = 1000

        tokens = import_statement.split()
        if len(tokens) > 1:
            pkg = tokens[1]  # import <pkg>, from <pkg> import ...
            _line, _col = funcref('line')('.'), funcref('col')('.')
            try:
                funcref('cursor')(1, 1)
                ln = funcref('search')(r'\v^(from|import) {}'.format(pkg),
                              'n', max_lines)
                if ln:  # a line for similar module was found
                    return ln
            finally:
                funcref('cursor')(_line, _col)

        # find a non-empty line
        for ln, bline in enumerate(buf, start=LineNumber(1)):
            if ln > max_lines: break  # do not scan too many lines

            if bline == '':
                continue
            if self.get_syngroup_at_line(ln) in self.AVOID_SYNGROUPS:
                continue
            return ln

        # cannot resolve, put in the topmost line
        return 1


class DBLookupStrategy(PythonImportResolveStrategy):
    """Lookup the database as-is."""

    def __call__(self, symbol: str) -> Optional[ImportStatement]:
        if symbol in DB:
            return next(iter((DB[symbol])))
        return None


class ImportableModuleStrategy(PythonImportResolveStrategy):
    """Use pkgutil.iter_modules to get importable modules."""

    def __init__(self):
        self.importable_modules: List[str] = [
            module_info.name for module_info in pkgutil.iter_modules()]

    def __call__(self, symbol: str) -> Optional[ImportStatement]:
        if symbol in self.importable_modules:
            return 'import {}'.format(symbol)
        return None


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
