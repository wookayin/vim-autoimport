"""Vim-related utilities."""

import vim
import functools


def funcref_nvim(name: str):
    '''Wrap a vim function.'''
    return functools.partial(vim.call, name)


if hasattr(vim, 'Function'):
    funcref = vim.Function
else:
    funcref = funcref_nvim
