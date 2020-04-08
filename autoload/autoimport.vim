" autoload/autoimport.vim

"if exists("b:did_autoload_autoimport")
"    finish
"endif
"let b:did_autoload_autoimport = 1

" Setup (import python modules when first called)
py3 import vim
py3 import vim_autoimport

if exists('v:false') | let s:false = v:false | else | let s:false = 0 | endif
if exists('v:true')  | let s:true  = v:true  | else | let s:true  = 1 | endif


function! autoimport#__version__() abort
    " Returns __version__ string
    return py3eval('vim_autoimport.__version__')
endfunction

function! autoimport#__reload__(...) abort
    " Reload backing python modules (useful for debugging)
    let l:verbose = get(a:, 1, s:true)
    if l:verbose
      py3 vim_autoimport.__reload__(verbose=True)
    else
      py3 vim_autoimport.__reload__()
    endif
endfunction

function! autoimport#add_import(line) abort
    return py3eval('vim_autoimport.get_manager().add_import(vim.eval("a:line"))')
endfunction

function! autoimport#import_symbol(symbol) abort
    return py3eval('vim_autoimport.get_manager().import_symbol(vim.eval("a:symbol"))')
endfunction

function! autoimport#resolve_import(symbol) abort
    return py3eval('vim_autoimport.get_manager().resolve_import(vim.eval("a:symbol"))')
endfunction
