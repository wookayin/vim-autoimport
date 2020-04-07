" plugin/autoimport.vim

"if exists('g:did_plugin_autoimport') || &cp
"    finish
"endif
"let g:did_plugin_autoimport = 1

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
command! -bar -nargs=* ImportSymbol   call s:ImportSymbol(<f-args>)
function s:ImportSymbol(...)
  if a:0 > 1
    echohl WarningMsg | echom "Usage: ImportSymbol [symbol]" | echohl None
    return
  endif
  let l:query = get(a:, 1, expand("<cexpr>"))

  let l:ret = autoimport#import_symbol(l:query)
  if empty(l:ret)
    echohl WarningMsg | echom printf("Cannot resolve import for `%s`", l:query) | echohl None
  elseif l:ret['line'] > 0
    echohl Special | echom printf("Added to Line %d: %s", l:ret['line'], l:ret['statement']) | echohl None
  else
    echohl Normal | echom printf("Import for `%s` already exists, no changes", l:query) | echohl None
  endif
endfunction
