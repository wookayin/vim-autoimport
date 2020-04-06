"""The vim_autoimport module entrypoint."""

__version__ = '0.1.0.dev0'


def __reload__(verbose=False):
    import importlib, sys
    mods = []
    for modname in sys.modules:
        if modname.startswith('vim_autoimport'):
            importlib.reload(sys.modules[modname])
            mods.append(modname)

    if verbose:
        print("[DEBUG] Reloaded {} modules: {}".format(len(mods), mods))
    return mods


from .managers import get_manager
