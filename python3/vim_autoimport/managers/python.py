"""vim_autoimport.managers.python"""

import abc
import asyncio
import functools
import os
import pkgutil
import shutil
import sys
import sysconfig
from collections import defaultdict, namedtuple
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type

import vim

from .. import vim_utils
from ..vim_utils import echomsg, funcref
from .manager import AutoImportManager, LineNumber, StrategyNotReadyError

ImportStatement = str


@functools.total_ordering
class PyImport:
    package: str
    symbol: Optional[str]
    alias: Optional[str]
    __slots__ = ('package', 'symbol', 'alias')

    def __init__(self, package: str, symbol: Optional[str] = None,
                 alias: Optional[str] = None):
        self.package = package
        self.symbol = symbol
        self.alias = alias

    def __lt__(self, other):
        return (self.package, self.symbol or '', self.alias or '') < \
            (other.package, other.symbol or '', other.alias or '')

    def __eq__(self, other):
        return (self.package, self.symbol or '', self.alias or '') == \
            (other.package, other.symbol or '', other.alias or '')

    def __hash__(self):
        return hash((self.package, self.symbol or '', self.alias or ''))

    def __str__(self):
        if self.symbol:
            s = "from {} import {}".format(self.package, self.symbol)
        else:
            s = "import {}".format(self.package)
        if self.alias:
            s += " as {}".format(self.alias)
        return s

    def __repr__(self):
        return 'PyImport("{}")'.format(str(self))


class PythonImportResolveStrategy(abc.ABC):
    """Strategy interface for AutoImportManager.resolve_import(). All instances
    of its subclasses will be instantiated at each call of resolve_import()."""

    @abc.abstractmethod
    def __call__(self, symbol: str) -> Optional[PyImport]:
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

        self._strategies = self.create_strategies()

    def create_strategies(self) -> List[PythonImportResolveStrategy]:
        # ctags requires asyncio, which does not work on vim8.
        enable_ctags = vim_utils.is_neovim and shutil.which("ctags")
        strategies = [
            DBLookupStrategy(),
            ImportableModuleStrategy(),
            BuiltinCTagsStrategy() if enable_ctags else None,
            SitePackagesCTagsStrategy() if enable_ctags else None,
        ]
        return [s for s in strategies if s]

    async def wait_until_strategies_ready(self):
        """Wait until all async strategies complete their loading."""
        for s in self._strategies:
            if hasattr(s, '_future') and asyncio.isfuture(s._future):
                await s._future

    def resolve_import(self, symbol: str) -> Optional[str]:
        # p.a.c.k.a.g.e.symbol -> if any ancestor package is known, import it
        def _ancestor_packages(symbol_chain: str):
            yield symbol_chain  # itself first

            chain = symbol_chain.split('.')
            for k in range(1, len(chain)):
                yield '.'.join(chain[:-k])

        # apply candidates (symbol itself and its all ancestors),
        # and if any match is found by a strategy return it
        for candidate_symbol in _ancestor_packages(symbol):
            for strategy in self._strategies:
                r: Optional[PyImport] = None
                try:
                    r = strategy(candidate_symbol)
                except StrategyNotReadyError:
                    pass # TODO log
                if r:
                    assert isinstance(r, PyImport), (
                        "Wrong type given by %s : %s" % (strategy, type(r)))
                    return str(r)
        return None

    def is_import_statement(self, line: str) -> bool:
        line = line.strip()
        if '\n' in line:
            return False
        return line.startswith('from ') or line.startswith('import ')

    AVOID_SYNGROUPS = set(
        ['pythonString', 'pythonDocstring', 'pythonComment',
         '@comment', '@string.documentation']
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
        bline: str
        for ln, bline in enumerate(buf, start=LineNumber(1)):
            if ln > max_lines:
                break  # do not scan too many lines

            if bline == '':
                continue
            if self._get_hlgroups_at_line(ln) & self.AVOID_SYNGROUPS:
                continue
            return ln

        # cannot resolve, put in the topmost line
        return 1

    def list_all(self) -> Iterable[Tuple[str, List[Any]]]:
        """Enumerate all symbols from internal strategies."""
        # TODO: Support ImportableModuleStrategy just in case ctags is unavailable.
        maps = []
        for strategy in self._strategies:
            if not isinstance(strategy, CTagsStrategy):
                continue
            if not hasattr(strategy, '_tags'):
                # TODO: can we return a partial list and later refresh it?
                raise StrategyNotReadyError("ctags database hasn't been built")
            maps.append(strategy._tags)

        # TODO: Using ChainMap causes a weird bug where the former defaultdict
        # would create an unwanted entry with keys that exist in the latter.
        # We simply workaround this using copy. But why is that happening?
        #return list(collections.ChainMap(*maps).items())
        M = {}
        for m in maps[::-1]:
           M.update(m)
        return M.items()


class DBLookupStrategy(PythonImportResolveStrategy):
    """Lookup the database as-is."""

    def __call__(self, symbol: str) -> Optional[PyImport]:
        if symbol in DB:
            return next(iter((DB[symbol])))
        return None


class ImportableModuleStrategy(PythonImportResolveStrategy):
    """Use pkgutil.iter_modules to get importable modules."""

    def __init__(self):
        modules = list(pkgutil.iter_modules())
        self.importable_modules: List[str] = [
            module_info.name for module_info in modules]

    def __call__(self, symbol: str) -> Optional[PyImport]:
        if symbol in self.importable_modules:
            return PyImport(package=symbol)  # import {symbol}
        return None


class CTagsStrategy(PythonImportResolveStrategy):
    # TODO: It cannot import "exported" symbols, e.g. tf.Module
    # or aliased package names (e.g. _pytest).
    def __init__(self, is_async=True):
        # Work around a bug https://bugs.python.org/issue35621 where
        # create_subprocess_shell() does not work with neovim's eventloop
        _w = asyncio.get_child_watcher()
        if getattr(_w, '_loop', None) is None:
            _w.attach_loop(asyncio.get_event_loop())

        if not is_async:
            # block until database is built.
            asyncio.get_event_loop().run_until_complete(
                self._build_database())
        else:
            # build index from ctags in background without blocking UI.
            self._future = asyncio.ensure_future(self._build_database())

    async def _build_database(self) -> None:
        try:
            stdout = await self._run_ctags()
            self._tags = await self._create_database_from_stream(stdout)
            echomsg("[vim-autoimport] Indexing {} is complete.".format(
                self.lib_directory), hlgroup='MoreMsg')
        except Exception as e:
            # TODO: Handle exception when ctags is not available.
            # TODO: If exception happens, mark as failure rather than not-ready
            echomsg("[vim-autoimport] Error while running ctags: {}\n".format(e),
                    hlgroup='Error')
            vim_utils.print_exception(*sys.exc_info())

    ctags_options = ''

    @property
    def lib_directory(self):
        raise NotImplementedError   # subclass must override it.

    async def _run_ctags(self) -> asyncio.StreamReader:
        # Note: exuberant-ctags ignores python-kinds,  TODO: add warning!
        # so universal-ctags is highly recommended (much faster).
        cmd = ("ctags -f - --languages=python --python-kinds=-vm "
               "--exclude='test_*' --exclude='*_test' "
               "{} -R .".format(self.ctags_options))
        proc = await asyncio.create_subprocess_shell(
            cmd, cwd=self.lib_directory, limit=10 * 1024 * 1024,  # 10MB
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL)
        assert proc.stdout is not None
        return proc.stdout

    async def _create_database_from_stream(self, reader,
                                           ) -> Dict[str, List[PyImport]]:
        tags = defaultdict(list)
        async for line in reader:
            line = line.strip()
            if isinstance(line, bytes):
                line = line.decode("utf-8", errors='ignore')
            if not line or line.startswith('!'):
                continue
            columns = line.split('\t')
            if len(columns) >= 5:
                continue  # local (inner) class or function, do not index it
            symbol, filename, preview, tagtype = columns[:4]
            if not tagtype in ('c', 'f'):
                continue  # only accepts class or function
            if symbol == '__init__':
                continue  # overriding __init__, etc.

            # convert filename to full.named.package
            package: str = os.path.splitext(filename)[0].replace("/", ".")
            package_parent, _, package_rmost = package.rpartition('.')
            if (package_rmost.startswith('test_') or
                package_rmost.endswith('_test')):
                continue  # exclude test suites
            if package_rmost == '__init__':
                package = package[:-9]  # package.__init__ -> package
                package_parent, _, package_rmost = package.rpartition('.')

            tags[symbol].append(PyImport(package=package, symbol=symbol))
            # index the module itself as well
            tags[package].append(PyImport(package=package))
            if package_parent:
                tags[package_rmost].append(
                    PyImport(package=package_parent, symbol=package_rmost))
                tags[package_rmost + '.' + symbol].append(
                    PyImport(package=package_parent, symbol=package_rmost))

        # remove duplicates
        for key, lst in tags.items():
            if len(lst) > 1:
                tags[key] = list(sorted(set(lst)))

        return tags

    def __call__(self, symbol: str) -> Optional[PyImport]:
        if not hasattr(self, '_tags'):
            raise StrategyNotReadyError("ctags database hasn't been built")

        if symbol not in self._tags:
            return None

        # If multiple entries, ask user to choose one
        candidates: List[PyImport] = self._tags[symbol]
        if len(self._tags[symbol]) > 1:
            rv = vim_utils.ask_user([str(c) for c in candidates])
            if not rv:
                return None      # aborted, no import added
            idx = rv - 1
        elif len(self._tags[symbol]) == 1:
            idx = 0
        else:
            assert False, "tags cannot be empty! (symbol = {})".format(symbol)

        package = self._tags[symbol][idx]
        return package


class BuiltinCTagsStrategy(CTagsStrategy):
    lib_directory = sysconfig.get_paths()['stdlib']
    ctags_options = '--exclude="site-packages"'


class SitePackagesCTagsStrategy(CTagsStrategy):
    lib_directory = sysconfig.get_paths()['purelib']  # site-packages


# -----------------------------------------------------------------------------
# Commonsense database of python imports, determined by the current python
# TODO: Make this list configurable and overridable by users.

import collections, importlib, fnmatch
DB: Dict[str, List[PyImport]] = collections.defaultdict(list)

ALL = lambda pkg: importlib.import_module(pkg).__all__  # type: ignore
DIR = lambda pkg: [s for s in dir(importlib.import_module(pkg))
                   if not s.startswith('_')]
def PATTERN(*pats):
    return (lambda pkg: [s for s in ALL(pkg) if
                         any(fnmatch.fnmatch(s, pat) for pat in pats)])

# common builtin modules: export (selective) symbols that are quite obvious
# so could be imported directly (e.g. `from typing import Any`).
# @see https://docs.python.org/3/py-modindex.html
DB_MODULES_BUILTIN: Dict[str, Any] = {}
DB_MODULES_BUILTIN.update({mod: None for mod in (
    # highest priority no matter what
    'sys', 'os', 're', 'math', 'random',

    # builtin module subpackages that are obvious or needs additional import
    'collections.abc', 'concurrent.futures',
    'curses.ascii', 'curses.panel', 'curses.textpad',
    'encodings.idna', 'encodings.mbcs', 'encodings.utf_8_sig',
    'html.entities', 'html.parser',
    'http.client', 'http.cookiejar', 'http.cookies', 'http.server',
    'importlib.abc', 'importlib.machinery', 'importlib.resources',
    'importlib.util', 'multiprocessing.connection', 'multiprocessing.dummy',
    'multiprocessing.managers', 'multiprocessing.pool',
    'multiprocessing.shared_memory', 'multiprocessing.sharedctypes',
    'os.path', 'json.tool', 'logging.config', 'logging.handlers',
    'test.support', 'test.support.script_helper', 'unittest.mock',
    'urllib.error', 'urllib.parse', 'urllib.request',
    'urllib.response', 'urllib.robotparser',
    'xml.dom', 'xml.etree', 'xml.etree.ElementTree',
    'xml.parsers',

    # builtin, but not visible from pkgutil
    'time', 'atexit', 'builtins', 'errno', 'faulthandler', 'gc',
    'marshal', 'posix', 'zipimport',
    'binhex', 'dummy_threading', 'formatter', 'parser', 'symbol',
)})
DB_MODULES_BUILTIN.update({
    # common functions/classes (from ... import ...)
    'abc': ['ABC', 'ABCMeta', 'abstractclassmethod', 'abstractmethod',
            'abstractproperty', 'abstractstaticmethod'],
    'argparse': PATTERN('Argument*', '*Formatter'),
    'collections': ALL,
    'contextlib': ['contextmanager', 'nullcontext', 'closing'],
    'copy': ['deepcopy'],
    'dataclasses': ['dataclass', 'field', 'fields', 'asdict', 'astuple', 'is_dataclass', 'make_dataclass'],
    'enum': ['Enum', 'EnumMeta', 'Flag', 'IntEnum', 'IntFlag'],
    'functools': ALL,
    'glob': ['glob', 'iglob'],
    'importlib': ALL,
    'io': PATTERN('*IO*', 'Buffered*'),
    'itertools': DIR,
    'pathlib': ALL,
    'pprint': ALL,
    'typing': lambda pkg: filter(lambda s: s[0].isupper(), ALL(pkg)),

    # Not builtin, but common
    'torch': ['nn'],
    'PIL': ['Image', 'ImageDraw', 'ImageFont', 'ImageOps'],
})

DB_MODULES_IMPORT = [
    'numpy',
    'scipy',
    'scipy.misc',
    'matplotlib',
    'torch',
]
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
            # from {pkg} import {s}
            DB[s].append(PyImport(package=pkg, symbol=s))
        # import {pkg}
        DB[pkg].append(PyImport(package=pkg))

    for s in DB_MODULES_IMPORT:
        # import {s}
        DB[s].append(PyImport(package=s))
    for pkg, s in DB_MODULES_IMPORT_AS.items():
        # import {pkg} as {s}
        DB[s].append(PyImport(package=pkg, alias=s))
    return DB
