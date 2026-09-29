"""Helpers for notebooks, usable interactively and under batch execution.

`stop()` ends a notebook early: the cells below it are left unexecuted, both
when you hit "Run All" in Jupyter/VS Code and when the notebook is run
headless by nbclient (`fdtrg-studies/scripts/run_notebooks.py` reports such a
notebook as *stopped*, not as failed).

    from dunetrg.analysis.notebook import stop

    if geo_file is None:
        stop("no geometry file for this dataset")

No dependencies beyond the standard library, so importing it pulls in nothing
from the analysis stack.
"""

__all__ = ["StopExecution", "stop"]


class StopExecution(Exception):
    """Raised to end a notebook early, without a traceback.

    IPython calls ``_render_traceback_`` to display an exception, so returning
    an empty list keeps the output clean; the kernel and all its state stay
    alive. Outside IPython this behaves like any other exception.
    """

    def _render_traceback_(self):
        return [f"Execution stopped: {self}"] if str(self) else ["Execution stopped."]


def stop(reason: str = "") -> None:
    """End the notebook here; the cells below are not executed."""
    raise StopExecution(reason)
