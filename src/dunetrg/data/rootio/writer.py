"""
NtupleWriter: Write pandas DataFrames into ROOT files using uproot.

The DataFrame is split into events via groupby on a user-selected set of
"key" columns. Those key columns become scalar branches; all remaining
columns become variable-length vector branches (one entry per event).

Requires Python >= 3.12.
"""

import logging
from pathlib import Path
from collections.abc import Sequence

import awkward as ak
import numpy as np
import pandas as pd
import uproot

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Type aliases  (PEP 695 – Python 3.12+; plain `type` statement)
# ---------------------------------------------------------------------------

type BranchDict = dict[str, np.ndarray | ak.Array]
type DtypeKey   = tuple[str, int]          # (kind, itemsize)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DTYPE_MAP: dict[DtypeKey, str] = {
    ("i", 1): "int8",
    ("i", 2): "int16",
    ("i", 4): "int32",
    ("i", 8): "int64",
    ("u", 1): "uint8",
    ("u", 2): "uint16",
    ("u", 4): "uint32",
    ("u", 8): "uint64",
    ("f", 4): "float32",
    ("f", 8): "float64",
    ("b", 1): "bool",
}


def _infer_dtype(series: pd.Series) -> str:
    """Map a pandas Series dtype to a ROOT branch type-string.

    Falls back to ``float64`` for exotic or object dtypes.
    """
    key: DtypeKey = (series.dtype.kind, series.dtype.itemsize)
    return _DTYPE_MAP.get(key, "float64")


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class NtupleWriter:
    """Write one or more pandas DataFrames into ROOT TTrees in a single file.

    The file path and open mode are fixed at construction time.  The file is
    opened lazily on the first :meth:`write` or :meth:`extend` call so that
    no empty file is created if the writer is never used.

    Parameters
    ----------
    path:
        Destination ``.root`` file path.
    key_columns:
        Column names used as the groupby key.  Each unique combination of
        values defines one *event*.  These columns are stored as **scalar**
        branches (one value per event).
    tree_name:
        Default TTree name used when no per-call ``tree_name`` is supplied.
        Defaults to ``"Events"``.
    mode:
        ``"recreate"`` *(default)* – overwrite any existing file.
        ``"update"`` – open an existing file and add new trees to it.
    compression:
        uproot compression object (e.g. ``uproot.ZLIB(4)``, ``uproot.LZ4(4)``,
        ``uproot.ZSTD(5)``, or ``None`` for uncompressed).
        Defaults to ``uproot.LZ4(4)`` if not specified.
    chunk_size:
        Number of *events* to accumulate before flushing a basket to disk.
        Larger values use more memory but typically compress better.
        Defaults to ``1_000``.

    Examples
    --------
    Streaming write, multiple trees (context manager)::

        with NtupleWriter("out.root", key_columns=["run", "event"]) as w:
            for tp_batch, hit_batch in batches:
                w.extend(tp_batch,  tree_name="TrigPrim")
                w.extend(hit_batch, tree_name="Hits")

    One-shot writes into the same file::

        writer = NtupleWriter("out.root", key_columns=["run", "event"])
        writer.write(tp_df,  tree_name="TrigPrim")
        writer.write(hit_df, tree_name="Hits")
        writer.close()

    Single-tree (default ``tree_name="Events"``)::

        with NtupleWriter("out.root", key_columns=["run", "event"]) as w:
            for batch in batches:
                w.extend(batch)
    """

    def __init__(
        self,
        path: str | Path,
        key_columns: Sequence[str],
        tree_name: str = "Events",
        mode: str = "recreate",
        compression: object = uproot.LZ4(4),
        chunk_size: int = 1_000,
    ) -> None:
        if not key_columns:
            raise ValueError("`key_columns` must not be empty.")
        if mode not in ("recreate", "update"):
            raise ValueError(f"mode must be 'recreate' or 'update', got {mode!r}")

        self.path:        Path   = Path(path)
        self.key_columns: list[str] = list(key_columns)
        self.tree_name:   str    = tree_name
        self.mode:        str    = mode
        self.compression: object = compression
        self.chunk_size:  int    = chunk_size

        # Internal state – populated lazily on first write/extend
        self._root_file: uproot.WritableFile | None = None
        self._trees:     dict[str, object]          = {}   # name → writable tree

    # ------------------------------------------------------------------
    # Public API – one-shot write
    # ------------------------------------------------------------------

    def write(self, df: pd.DataFrame, tree_name: str | None = None) -> None:
        """Convert *df* to ROOT and append it to the named TTree.

        Parameters
        ----------
        df:
            Input DataFrame.  Must contain every column in ``key_columns``.
        tree_name:
            TTree to write into.  Defaults to ``self.tree_name``.
        """
        name = tree_name or self.tree_name
        self._ensure_open()
        self._validate_columns(df)
        branches = self._build_branch_dict(df)
        n_events = len(next(iter(branches.values())))

        if name not in self._trees:
            self._root_file[name] = branches
            self._trees[name] = self._root_file[name]
        else:
            self._root_file[name].extend(branches)

        _log.info(
            f"Wrote {n_events:,} events ({len(df):,} rows) → '{self.path}' / '{name}'"
        )

    # ------------------------------------------------------------------
    # Public API – streaming / incremental write
    # ------------------------------------------------------------------

    def extend(self, df: pd.DataFrame, tree_name: str | None = None) -> None:
        """Append *df* (after groupby-splitting) to the named TTree.

        Parameters
        ----------
        df:
            Input DataFrame.  Must contain every column in ``key_columns``.
        tree_name:
            TTree to extend.  Defaults to ``self.tree_name``.
        """
        name = tree_name or self.tree_name
        self._ensure_open()
        self._validate_columns(df)
        branches = self._build_branch_dict(df)
        n_events = len(next(iter(branches.values())))

        if name not in self._trees:
            self._root_file[name] = branches
            self._trees[name] = self._root_file[name]
        else:
            self._root_file[name].extend(branches)

        _log.info(f"Appended {n_events:,} events ({len(df):,} rows) → '{name}'")

    def close(self) -> None:
        """Flush and close the underlying ROOT file."""
        if self._root_file is not None:
            self._root_file.close()
            self._root_file = None
            self._trees     = {}

    def __enter__(self) -> "NtupleWriter":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_open(self) -> None:
        """Open the ROOT file on first use."""
        if self._root_file is None:
            opener = uproot.recreate if self.mode == "recreate" else uproot.update
            self._root_file = opener(str(self.path), compression=self.compression)

    def _validate_columns(self, df: pd.DataFrame) -> None:
        missing = [c for c in self.key_columns if c not in df.columns]
        if missing:
            raise ValueError(f"key_columns not found in DataFrame: {missing}")

    def _build_branch_dict(self, df: pd.DataFrame) -> BranchDict:
        """Build the ``{branch_name: array}`` dict expected by uproot.

        Scalar branches (key columns)
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        One value per event, taken from the *first* row of each group.
        All rows within a group share the same key-column values by
        construction, so taking the first is always correct.

        Vector branches (remaining columns)
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        All non-key columns are collected into awkward jagged arrays –
        one variable-length sub-array per event.  The group order matches
        the scalar branches exactly.
        """
        vector_cols = [c for c in df.columns if c not in self.key_columns]
        groups      = df.groupby(self.key_columns, sort=False)

        # ── scalar branches ────────────────────────────────────────────
        first_rows  = groups.first().reset_index()
        scalar_data: dict[str, np.ndarray] = {
            col: first_rows[col].to_numpy().astype(_infer_dtype(first_rows[col]))
            for col in self.key_columns
        }

        # ── vector branches ────────────────────────────────────────────
        # groups.indices: dict[group_key → np.ndarray of row positions]
        # The dict preserves the same insertion order as `groups.first()`.
        group_indices = groups.indices
        vector_data: dict[str, ak.Array] = {}

        for col in vector_cols:
            dtype_str = _infer_dtype(df[col])
            col_np    = df[col].to_numpy().astype(dtype_str)
            vector_data[col] = ak.Array(
                [col_np[idx] for idx in group_indices.values()]
            )

        return scalar_data | vector_data   # PEP 584 dict merge (Python 3.9+)
