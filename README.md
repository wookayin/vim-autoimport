vim-autoimport
==============

A vim plugin for easily adding import statements.

*This is still WIP* --- things might change rapidly.


Usage
-----

Currently only works **for python**. You need to have `has('python3')` enabled.

Commands:

```vim
:ImportSymbol             " Add an import statement for the current symbol
:ImportSymbol np.zeros    " Add an import statement for the given expression (e.g. np.zeros)
```

Recommended keymappings:

```vim
nmap <silent> <M-CR>   :ImportSymbol<CR>
imap <silent> <M-CR>   <Esc>:ImportSymbol<CR>a
```

Tip: How to sort imports?

```vim
command! -buffer ImportOrganize    :CocCommand python.sortImports
```

License
-------

The MIT License (c) 2020 Jongwook Choi (@wookayin)
