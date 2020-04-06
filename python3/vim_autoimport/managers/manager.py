"""vim_autoimport.managers.manager"""

import re
from typing import Optional
from abc import ABC, abstractmethod

import vim


class AutoImportManager(ABC):

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
    def determine_linenumber(self, import_statement: str) -> int:
        '''Determines the line number (0-indexed) to place the import
        statement for the current vim buffer.'''
        raise NotImplementedError

    def get_syngroup_at_line(self, line_nr: int) -> str:
        '''Get the syntax group name for the given line (0-indexed)
        in the current buffer.'''
        synid = vim.call('synID', line_nr + 1, 1, 1)
        syntaxgroup = vim.call('synIDattr', synid, 'name')
        return syntaxgroup

    def import_symbol(self, symbol: str) -> bool:
        '''Add an import statement for the given symbol.'''
        import_statement = self.resolve_import(symbol)
        if not import_statement:
            return False

        return self.add_import(import_statement)

    def add_import(self, import_statement: str) -> bool:
        '''Add a raw import statement to the current buffer,
        at a proper location. Returns True iff the line was added.'''
        if not self.is_import_statement(import_statement):
            raise ValueError("Not a import statement: {}".format(import_statement))

        buf = vim.current.buffer
        def getline(line_nr: int):
            return buf[line_nr]

        # TODO: need to determine the current symbol was imported or not (or
        # it can be existing alias, variables, etc.) being semantics-aware.

        # Prevent duplicated import lines.
        if self.find_line(buf, import_statement) < 0:
            line_nr: int = self.determine_linenumber(import_statement)

            #prevline: str = getline(line_nr - 1) if line_nr > 0 else ''
            #if prevline and self.is_import_statement(prevline):
            #    vim.call('append', line_nr, 'ABOVE')
            #    line_nr += 1
            vim.call('append', line_nr, import_statement.rstrip())

            # Insert reasonable blank lines below
            # TODO: This behavior can be language-specific.
            if line_nr + 1 < len(buf) and \
                    not self.is_import_statement(getline(line_nr + 1)):
                vim.call('append', line_nr + 1, '')

        return True

    def find_line(self, buf, line: str) -> int:
        '''Search for the line in the buffer (to avoid duplicate imports),
        after stripping out comments.
        Returns 0-indexed line number if found, or -1 if not found.'''
        for i, bline in enumerate(buf):
            if i > 100: break  # do not scan too many lines
            bline = re.sub(r"\s*#.*$", '', bline).rstrip()
            if bline == line:
                return i
        return -1
