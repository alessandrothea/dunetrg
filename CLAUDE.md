# dunetrg — Claude context

## What this is
One installable package holding the three DUNE trigger-primitive libraries as
submodules: `dunetrg.data`, `dunetrg.emu`, `dunetrg.analysis`. Single
repository, single distribution, single version.

## Toolchain
- **Python 3.13** (`.python-version`); **uv** for everything, never pip.
  - `uv sync --all-extras` for a full dev environment
  - `uv run pytest`, `uv run lint-imports`
- Optional extras: `[emu]`, `[analysis]`, `[all]`. The base install carries
  only what `dunetrg.data` needs, so don't add a plotting or numba import to
  `dunetrg.data` — it would break the light install.

## Layout (`src/dunetrg/`)
| Path | Purpose |
|---|---|
| `data/rootio/` | ROOT I/O (`NtupleReader`, `NtupleWriter`) |
| `data/workspace.py` | `TrgDataFrame`, workspaces |
| `data/datacatalogue.py` | YAML dataset catalogue; resolves dirs via `DTRG_DATA_ROOT` |
| `data/geometry/` | detector geometry + bundled JSON, loaded via `importlib.resources` |
| `data/utils.py` | `temporary_log_level`, `pandas_backend`, `fieldswapper` |
| `emu/tpg/`, `emu/tafinder/`, `emu/cli/` | TPG emulation, TA finding, `ta-finder` |
| `analysis/` | `histograms`, `base`, `snn`, `tawindows`, `tpfilter`, `utils`, `notebook` (`stop()`) |
| `analysis/viz/` | plotters; `analysis/cli/` | `tawin-util` |

## Layering (enforced, `uv run lint-imports`)
`dunetrg.data` must not import `dunetrg.emu`/`dunetrg.analysis` or matplotlib;
`dunetrg.data.geometry` must not import rootio/workspace/datacatalogue or
uproot/awkward/pandas; `dunetrg.emu` must not import `dunetrg.analysis` or the
plotting stack; `dunetrg.analysis` must not import `dunetrg.emu`. The known
`analysis <-> viz` cycle inside `dunetrg.analysis` is accepted for now.

## Test conventions
- Every assert is preceded by a `print()` of computed vs expected values, so
  `pytest -vs` is readable. Prefer f-strings. Skip prints only for
  `pytest.raises`.
- Tests live in `test/{data,emu,analysis}` and run with importlib import mode.
