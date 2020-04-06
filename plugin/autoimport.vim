" plugin/autoimport.vim

if exists('g:did_plugin_autoimport') || &cp
    finish
endif
let g:did_plugin_autoimport = 1

if version < 704
    echohl WarningMsg | echom "vim-autoimport requires Vim 7.4+" | echohl None
    finish
endif

" TODO: Require python3.5+
if !has('python3')
    echohl WarningMsg | echom "vim-autoimport requires has('python3') with Python 3.5+" | echohl None
    finish
endif


" Commands.
command! -nargs=0 ImportSymbol   call s:ImportSymbol()
function s:ImportSymbol()
  let cexpr = expand("<cexpr>")
  if !autoimport#import_symbol(cexpr)
    echom printf("Cannot resolve import for `%s`", cexpr)
  endif
endfunction
