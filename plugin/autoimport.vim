" plugin/autoimport.vim

if exists('g:did_plugin_autoimport') || &cp
    finish
endif
let g:did_plugin_autoimport = 1

if version < 704
    echohl WarningMsg | echom "vim-autoimport requires Vim 7.4+" | echohl None
    finish
endif
if !has('python3')
    echohl WarningMsg | echom "vim-autoimport requires has('python3')" | echohl None
    finish
endif
