
function! autoimport#utils#get_cexpr() abort
  " Get a expression or symbol under cursor.  Similar to expand("<cexpr>"),
  " but it also works well right after '.' or '(' characters.
  let cexpr = expand("<cexpr>")
  if !(cexpr[0] == '.' || cexpr[0] == '(')
    return cexpr
  endif

  " try at one column left
  let [line, column] = [line('.'), col('.')]
  call cursor(line, column - 1)
  try
    let cexpr = expand("<cexpr>")
    return cexpr
  finally
    call cursor(line, column)
  endtry
endfunction
