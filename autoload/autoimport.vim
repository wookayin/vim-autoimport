" autoload/autoimport.vim

"if exists("b:did_autoload_autoimport")
"    finish
"endif
"let b:did_autoload_autoimport = 1

" Setup (import python modules when first called)
py3 import vim
py3 import vim_autoimport

function! autoimport#__version__() abort
    " Returns __version__ string
    return py3eval('vim_autoimport.__version__')
endfunction

function! autoimport#__reload__() abort
    " Reload backing python modules (useful for debugging)
    py3 import importlib
    py3 importlib.reload(vim_autoimport)
endfunction
