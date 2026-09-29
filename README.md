# dunetrg

DUNE trigger-primitive libraries, as one installable package with three
submodules:

| Module | What it does | Extra |
|---|---|---|
| `dunetrg.data` | ROOT I/O, workspace data model, dataset catalogue, detector geometry | core |
| `dunetrg.emu` | TPG firmware emulation, DBSCAN TA finder, the `ta-finder` CLI | `[emu]` |
| `dunetrg.analysis` | histograms, selections, efficiencies, plotting, the `tawin-util` CLI | `[analysis]` |

Dependencies run one way: `emu` and `analysis` both build on `data`, and never
on each other. Import-linter contracts in `pyproject.toml` enforce it, and
`dunetrg.data.geometry` additionally stays free of I/O and of uproot, awkward
and pandas.

## Install

```bash
pip install dunetrg                  # data only: uproot, awkward, pandas, pydantic, …
pip install "dunetrg[emu]"           # + numba, scikit-learn, scipy
pip install "dunetrg[analysis]"      # + matplotlib, hist, mplhep, particle, …
pip install "dunetrg[all]"
```

Importing a submodule without its extra fails on the missing third-party
package; that's the trade for keeping the base install light. The `ta-finder`
and `tawin-util` commands need `[emu]` and `[analysis]` respectively.

From git, until it is published:

```toml
[tool.uv.sources]
dunetrg = { git = "ssh://git@github.com/alessandrothea/dunetrg.git", rev = "v0.1.0" }
```

## Development

```bash
uv sync --all-extras
uv run pytest            # test/{data,emu,analysis}
uv run lint-imports      # the four contracts
```

Tests use `--import-mode=importlib`, because `test/data` and `test/analysis`
both contain `test_utils.py`.

## Data

Datasets are located through `DTRG_DATA_ROOT`, which points at the data
directory itself, so `dunetrg.data.datacatalogue.load('vd/1x8x14/preprod')`
reads `$DTRG_DATA_ROOT/vd/1x8x14/preprod/`, where that dataset's
`datacatalogue.yaml` lives. Pass `data_root=` to override it per call.

## Origin

Split out of `tpvalidator` (see `MIGRATION_PLAN_v2.md` in the parent tree).
This single-package layout is the mark_4 variant; mark_2 kept three separate
repositories and mark_3 a uv workspace of three packages.
