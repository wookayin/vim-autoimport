import vim
from typing import Optional, Dict

from .manager import AutoImportManager as AutoImportManager
from .manager import StrategyNotReadyError as StrategyNotReadyError


# A cache for singleton manager instances (one per filetype)
INSTANCES: Dict[str, AutoImportManager] = {}


def get_manager(filetype: Optional[str] = None,
                ) -> AutoImportManager:
    """Get a AutoImportManager instance for the current or specified filetype.

    If a manager instance for the same filetype was created before, the same
    instance will be retrieved (i.e., singleton).
    """
    if filetype is None:
        filetype = vim.eval('&filetype')

    if not filetype:
        raise ValueError("Unknown filetype.")

    # TODO: use a thread lock.
    manager = INSTANCES.get(filetype, None)
    if manager is not None:
        return manager

    if filetype == 'python':
        from .python import PythonImportManager
        manager = PythonImportManager()
    else:
        raise NotImplementedError("Sorry, currently only python is supported.")

    INSTANCES[filetype] = manager
    return manager
