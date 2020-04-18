from functools import partial

import vim


def funcref(name):
    if vim.eval("has('nvim')") == "1":
        func = partial(vim.call, name)
    else:
        func = vim.Function(name)
    return func
