import sys

import pytest
import unittest.mock as mock

import vim  # pylint: disable=import-error
from vim_autoimport import vim_utils


def testFuncrefVim():
    vim.Function = mock.MagicMock()
    vim.Function("vim#function#echovim").return_value = b'vim'
    vim.Function("vim#function#echovim").__repr__ = lambda self: "<vim.Function 'vim#function#echovim'>"

    func = vim_utils.VimFunctionWrapper("vim#function#echovim")
    print("\nfuncref:", func)
    assert '<locals>' not in repr(func)  # do we have pretty name?
    assert 'vim#function#echovim' in repr(func)

    r = func("hello")
    assert isinstance(r, str) and r == 'vim'

    vim.Function.assert_called_with("vim#function#echovim")
    vim.Function("vim#function#echovim").assert_called_with("hello")


def testFuncrefNvim():
    vim.call = mock.MagicMock(return_value='nvim')
    vim.call.__repr__ = lambda self: '<bound method Nvim.call of <pynvim.plugin.script_host.LegacyVim object at 0x00>>'

    func = vim_utils.funcref_nvim("vim#function#echovim")
    print("\nfuncref:", func)
    assert func("hello") == 'nvim'

    vim.call.assert_called_with("vim#function#echovim", "hello")


if __name__ == '__main__':
    pytest.main(["-s", "-v"] + sys.argv)
