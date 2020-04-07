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
  let l:ret = autoimport#import_symbol(cexpr)
  if empty(l:ret)
    echohl WarningMsg | echom printf("Cannot resolve import for `%s`", cexpr) | echohl None
  elseif l:ret['line'] > 0
    echohl Special | echom printf("Added to Line %d: %s", l:ret['line'], l:ret['statement']) | echohl None
  else
    echohl Normal | echom printf("Import for `%s` already exists, no changes", cexpr) | echohl None
  endif
endfunction
