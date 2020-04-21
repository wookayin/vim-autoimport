"""Vim-related utilities."""

import vim
import functools


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
