import pandas as pd
from contextlib import contextmanager


@contextmanager
def temporary_log_level(logger, level):
    """Change the logger message level within the context.
    Restore the previous level at context exit.
    """
    old_level = logger.level
    logger.setLevel(level)
    yield
    logger.setLevel(old_level)


@contextmanager
def pandas_backend(backend):
    """Change the pandas graphical backend within the context.
    Restore the previous backend at context exit.
    """
    current_backend = pd.options.plotting.backend
    pd.options.plotting.backend = backend
    yield
    pd.options.plotting.backend = current_backend


@contextmanager
def fieldswapper(obj:object, name:str, value):

    oldval = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield obj
    finally:
        setattr(obj, name, oldval)
