"""vim_autoimport.managers.manager"""

import itertools
import re
from typing import Set
from typing import Any, Dict, Optional, List, Tuple, Iterable
from abc import ABC, abstractmethod

import vim

from ..vim_utils import funcref, is_treesitter_supported


LineNumber = int     # 1-indexed line number as integer.


class StrategyNotReadyError(RuntimeError):
    pass


class AutoImportManager(ABC):
    # TODO: Define life-cycle or reusability of Manager classes.

    def __init__(self):
        pass

    @abstractmethod
    def resolve_import(self, symbol: str) -> Optional[str]:
        '''Resolve a import statement for the given symbol.
        If not resolvable, return None.'''
        raise NotImplementedError

    @abstractmethod
    def is_import_statement(self, line: str) -> bool:
        '''Tells whether the given line is a import statement.'''
        return False

    @abstractmethod
    def determine_linenumber(self, import_statement: str) -> LineNumber:
        '''Determines the line number (1-indexed) to place the import
        statement for the current vim buffer.'''
        raise NotImplementedError

    def _get_hlgroups_at_line(self, line_nr: LineNumber) -> Set[str]:
        '''Get all the names of syntax groups in the given line (1-indexed),
        for the current buffer.'''

        # Vanilla vim syntax
        synid = funcref('synID')(line_nr, 1, 1)  # lnum, col, trans
        syntaxgroup = funcref('synIDattr')(synid, 'name')
        if syntaxgroup:
            return set([syntaxgroup])

        # treesitter (requires nvim 0.9.0+)
        if is_treesitter_supported:
            # treesitter hlgroups are prefixed with '@' like a capture
            captures = vim.lua.vim.treesitter.get_captures_at_pos(0, line_nr - 1, 0)
            if captures:
                return set('@' + t['capture'] for t in captures)

        # TODO: Support non-treesitter extmark highlights (e.g. semshi)
        return set()  # not found

    def import_symbol(self, symbol: str) -> Dict[str, Any]:
        '''Add an import statement for the given symbol.'''
        import_statement = self.resolve_import(symbol)
        if not import_statement:
            return {}

        line_nr: LineNumber = self.add_import(import_statement)
        if line_nr > 0:
            return {'statement': import_statement, 'line': line_nr}
        else:  # already exists
            return {'statement': import_statement, 'line': 0}

    def add_import(self, import_statement: str) -> LineNumber:
        '''Add a raw import statement line to the current buffer,
        at a proper location.

        Returns the line number (1-indexed) at which the line was added,
        or 0 if no change was made (e.g. there is a duplicate).
        '''
        if not self.is_import_statement(import_statement):
            raise ValueError("Not a import statement: {}".format(import_statement))

        buf = vim.current.buffer
        def getline(line_nr: LineNumber):
            return buf[line_nr - 1]
        def insertline(line_nr: LineNumber, line: str):
            return funcref('append')(line_nr - 1, line)

        # TODO: need to determine the current symbol was imported or not (or
        # it can be existing alias, variables, etc.) being semantics-aware.

        # Prevent duplicated import lines.
        line_nr_existing = self.find_line(buf, import_statement)
        if line_nr_existing:
            return 0

        line_nr: LineNumber = self.determine_linenumber(import_statement)
        insertline(line_nr, import_statement.rstrip())

        # Insert reasonable blank lines below
        # TODO: This behavior can be language-specific.
        if line_nr + 1 <= len(buf) and \
                not self.is_import_statement(getline(line_nr + 1)):
            insertline(line_nr + 1, '')

        return line_nr

    def find_line(self, buf, line: str) -> LineNumber:
        '''Search for the line in the buffer (to avoid duplicate imports),
        after stripping out comments.
        Returns 1-indexed line number if found, or 0 if not found.'''
        i: LineNumber
        for i, bline in enumerate(buf, start=LineNumber(1)):
            if i > 100: break  # do not scan too many lines
            bline = re.sub(r"\s*#.*$", '', bline).rstrip()
            if bline == line:
                return i
        return 0

    def list_all(self) -> Iterable[Tuple[str, List[Any]]]:
        return []

    def suggest(self, query='', max_items=50) -> Dict[str, List[str]]:
        try:
            # TODO: we need some proper ranking and fuzzy search.
            items = ((k, list(map(str, v))) for (k, v) in self.list_all()
                    if k.startswith(query))
            return dict(itertools.islice(items, 0, max_items))
        except StrategyNotReadyError:
            return {}
