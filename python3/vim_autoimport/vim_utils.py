"""Vim-related utilities."""

import vim
import sys
import functools
import traceback
from typing import Optional


# Whether the python host is neovim or vanilla vim.
is_neovim = hasattr(vim, '__module__')


def funcref_nvim(name: str):
    '''Wrap a nvim function.'''
    return functools.partial(vim.call, name)


class VimFunctionWrapper:
    '''Wrap a vim function (vim.Function)'''
    def __init__(self, name: str):
        self._fn = vim.Function(name)

    def __call__(self, *args, **kwargs):
        ret = self._fn(*args, **kwargs)
        if isinstance(ret, bytes):
            # for string return values, need to decode to str
            return ret.decode('utf8')
        return ret

    def __repr__(self):
        return 'VimFunctionWrapper(' + repr(self._fn) + ')'


if hasattr(vim, 'Function'):
    funcref = VimFunctionWrapper
else:
    funcref = funcref_nvim


def echomsg(msg: str, hlgroup=None):
    """Execute vim's echomsg synchronously."""
    try:
        funcref("autoimport#utils#echomsg")(msg, hlgroup)
    except:
        # neovim API has a bug (pynvimm#355), need to workaround
        # AttributeError: 'NoneType' object has no attribute 'switch'
        pass

if not hasattr(vim, 'Function') and not hasattr(vim, 'call'):
    # maybe in mock/unittest?
    def _echomsg_mock(msg: str, hlgroup=None):
        sys.stderr.write(msg)
        sys.stderr.write('\n')
        sys.stderr.flush()
    echomsg = _echomsg_mock


def print_exception(etype, value, tb, limit=None, chain=True):
    """e.g. print_exception(*sys.exc_info())"""
    e = traceback.format_exception(etype, value, tb, limit=limit, chain=chain)
    stacktrace = '\n'.join(e).split('\n')
    for line in stacktrace:
        echomsg(line.rstrip(), hlgroup='WarningMsg')


def ask_user(items) -> Optional[int]:
    """Ask user to select one of the list (numbered 1 through N)."""
    items = ["[%2d] " % i + item
             for i, item in enumerate(items, start=1)]
    try:
        rv = vim.eval("inputlist(%s)" % items)    # TODO: escape properly
        vim.command('echo " "')
        rv = int(rv) if (rv and rv != "0") else None
        return rv
    except Exception as e:
        if isinstance(e, KeyboardInterrupt) or str(e) == "Keyboard interrupt":
            rv = None        # user abort
        else:
            raise
