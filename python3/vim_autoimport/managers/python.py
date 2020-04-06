"""vim_autoimport.managers.python"""

from typing import Optional
from collections import namedtuple

import vim

from .manager import AutoImportManager


class PythonImportManager(AutoImportManager):
    """A import manager for Python.

    Currently it only lookups a pre-defined database for resolving imports,
    but could be smarter being aware of LSP, ctags, regexp-based importable
    symbols from site-packages or the current project tree, etc.
    """

    def __init__(self):
        pass

    def resolve_import(self, symbol: str) -> Optional[str]:
        return DB.get(symbol, None)

    def is_import_statement(self, line: str):
        line = line.strip()
        if '\n' in line:
            return False
        return line.startswith('from ') or line.startswith('import ')

    AVOID_SYNGROUPS = set(
        ['pythonString', 'pythonDocstring', 'pythonComment']
    )

    def determine_linenumber(self, import_statement: str) -> int:
        # TODO: Find a correct place for import,
        # being aware of docstrings, import statements, etc.
        buf = vim.current.buffer

        for ln, bline in enumerate(buf, start=0):
            if ln > 100: break  # do not scan too many lines

            if bline == '':
                continue
            if self.get_syngroup_at_line(ln) in self.AVOID_SYNGROUPS:
                continue
            return ln

        # cannot resolve, put in the topmost line
        return 0


# -----------------------------------------------------------------------------
# Commonsense database of python imports
# TODO: Make this list configurable by users.
DB = {}

import typing
for s in typing.__all__:
    DB[s] = 'from typing import %s' % s

DB_MODULES_BUILTIN = ['re', 'os', 'sys',
                      'importlib', 'pathlib', 'contextlib']
DB_MODULES_COMMON = ['numpy', 'scipy', 'matplotlib']

for s in DB_MODULES_BUILTIN + DB_MODULES_COMMON:
    DB[s] = 'import ' + s

DB_MODULES_AS = {
    'numpy': 'np', 'pandas': 'pd', 'matplotlib.pyplot': 'plt'
}
for m, s in DB_MODULES_AS.items():
    DB[s] = 'import {} as {}'.format(m, s)

# -----------------------------------------------------------------------------
