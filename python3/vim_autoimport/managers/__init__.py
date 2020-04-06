import vim
from typing import Optional

from .manager import AutoImportManager


def get_manager(filetype: Optional[str] = None,
                ) -> AutoImportManager:
    if filetype is None:
        filetype = vim.eval('&filetype')

    # TODO: should reuse the cached instance per filetype (should be the case)
    # or re-create manager instances every time?
    if filetype == 'python':
        from .python import PythonImportManager
        return PythonImportManager()
    else:
        raise NotImplementedError
