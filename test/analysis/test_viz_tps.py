"""Tests for TrgPrimitivesPlotter origin projections."""
from types import SimpleNamespace

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from dunetrg.analysis.viz.tps import TrgPrimitivesPlotter


@pytest.fixture
def origin_tps():
    rng = np.random.default_rng(2)
    # Generator sizes on plane 2 (signal): GenA=60, GenB=30, GenC=10
    gens = ["GenA"] * 60 + ["GenB"] * 30 + ["GenC"] * 10
    n_sig = len(gens)
    sig = pd.DataFrame({
        "bt_generator_name": gens,
        "bt_is_signal": 1,
        "readout_plane_id": 2,
    })
    # Noise TPs on plane 2 and signal TPs on plane 0: both must be excluded
    noise = pd.DataFrame({"bt_generator_name": [""] * 20, "bt_is_signal": 0, "readout_plane_id": 2})
    other_plane = pd.DataFrame({"bt_generator_name": ["GenD"] * 80, "bt_is_signal": 1, "readout_plane_id": 0})
    df = pd.concat([sig, noise, other_plane], ignore_index=True)
    for c in ("bt_primary_x", "bt_primary_y", "bt_primary_z"):
        df[c] = rng.uniform(-300, 300, len(df))
    df["sample_start"] = rng.integers(0, 8000, len(df))
    return df


@pytest.fixture
def plotter(origin_tps):
    ws = SimpleNamespace(
        tps=origin_tps,
        mctruth_blocks_map={0: "GenA", 1: "GenB", 2: "GenC", 3: "GenD"},
        info={"geo": {"detector": "dunevd10kt_3view_30deg_v5_refactored_1x8x14ref"}},
    )
    return TrgPrimitivesPlotter(ws)


class TestTopGeneratorGroups:

    def test_sorted_by_size(self, plotter, origin_tps):
        df = origin_tps.query("bt_is_signal == 1 & readout_plane_id == 2")
        groups = plotter._top_generator_groups(df)
        names = [n for n, _ in groups]
        sizes = [len(g) for _, g in groups]
        print(f"\nnames={names}, sizes={sizes}, expected names=['GenA', 'GenB', 'GenC'], sizes=[60, 30, 10]")
        assert names == ["GenA", "GenB", "GenC"]
        assert sizes == [60, 30, 10]

    def test_n_top_truncates(self, plotter, origin_tps):
        groups = plotter._top_generator_groups(origin_tps, n_top=2)
        names = [n for n, _ in groups]
        print(f"\nnames={names}, expected=['GenD', 'GenA']")
        assert names == ["GenD", "GenA"]


class TestPlotOriginProjectionsByGenerator:

    def test_layout_and_legend(self, plotter):
        fig = plotter.plot_origin_projections_by_generator(rop=2)
        axes = fig.axes
        titles = [ax.get_title() for ax in axes[:3]]
        legend = axes[3].get_legend()
        labels = [t.get_text() for t in legend.get_texts()]
        print(f"\nn_axes={len(axes)}, expected=4")
        print(f"titles={titles}, expected=['Y-X view', 'Z-X view', 'Y-Z view']")
        print(f"legend labels={labels}, expected=['GenA', 'GenB', 'GenC']")
        assert len(axes) == 4
        assert titles == ["Y-X view", "Z-X view", "Y-Z view"]
        assert labels == ["GenA", "GenB", "GenC"]
        plt.close(fig)

    def test_selection_excludes_noise_and_other_planes(self, plotter):
        fig = plotter.plot_origin_projections_by_generator(rop=2)
        n_points = sum(len(c.get_offsets()) for c in fig.axes[0].collections)
        print(f"\nn_points in Y-X view={n_points}, expected=100")
        assert n_points == 100
        plt.close(fig)

    def test_query_and_n_top(self, plotter, origin_tps):
        fig = plotter.plot_origin_projections_by_generator(rop=2, n_top=2, query="sample_start < 4000")
        sel = origin_tps.query("bt_is_signal == 1 & readout_plane_id == 2 & sample_start < 4000")
        expected = int(sel.bt_generator_name.value_counts().iloc[:2].sum())
        n_points = sum(len(c.get_offsets()) for c in fig.axes[0].collections)
        n_labels = len(fig.axes[3].get_legend().get_texts())
        print(f"\nn_points={n_points}, expected={expected}; n_labels={n_labels}, expected=2")
        assert n_points == expected
        assert n_labels == 2
        plt.close(fig)

    def test_too_few_colors_raises(self, plotter):
        with pytest.raises(ValueError):
            plotter.plot_origin_projections_by_generator(rop=2, colors=[0])
