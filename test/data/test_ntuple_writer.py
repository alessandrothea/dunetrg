import numpy as np
import pandas as pd
import awkward as ak
import uproot
import pytest

from dunetrg.data.rootio.writer import NtupleWriter


def _make_df(seed: int, n_events: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = [
        {
            "run":        1,
            "lumi":       evt // 10 + 1,
            "event":      evt,
            "hit_x":      rng.uniform(-100, 100),
            "hit_y":      rng.uniform(-100, 100),
            "hit_charge": rng.exponential(50),
            "hit_layer":  int(rng.integers(0, 4)),
        }
        for evt in range(n_events)
        for _   in range(int(rng.integers(1, 8)))
    ]
    return pd.DataFrame(rows)


class TestNtupleWriterRoundTrip:
    def test_two_trees_context_manager(self, tmp_path):
        tp_df  = _make_df(42)
        hit_df = _make_df(99)
        out_path = tmp_path / "out.root"

        with NtupleWriter(out_path, key_columns=["run", "lumi", "event"]) as w:
            w.extend(tp_df,  tree_name="TrigPrim")
            w.extend(hit_df, tree_name="Hits")

        with uproot.open(out_path) as f:
            tree_names = {k.split(";")[0] for k in f.keys()}
            print(f"\nTrees in file: {sorted(tree_names)}, expected: {{'TrigPrim', 'Hits'}}")
            assert tree_names == {"TrigPrim", "Hits"}

            for tname, src_df in (("TrigPrim", tp_df), ("Hits", hit_df)):
                tree = f[tname]
                n_events_expected = src_df["event"].nunique()
                print(f"\nTTree '{tname}' num_entries: {tree.num_entries}, expected: {n_events_expected}")
                assert tree.num_entries == n_events_expected

                arrays = tree.arrays(library="ak")
                df = ak.to_dataframe(arrays)

                got_rows = len(df)
                print(f"round-tripped row count for '{tname}': {got_rows}, expected: {len(src_df)}")
                assert got_rows == len(src_df)

                got_cols = set(df.columns.get_level_values(0)) if isinstance(df.columns, pd.MultiIndex) else set(df.columns)
                expected_cols = set(src_df.columns) - {"run", "lumi", "event"}
                # scalar (key) branches are also present as columns after ak.to_dataframe
                print(f"vector branches present for '{tname}': {expected_cols <= got_cols}")
                assert expected_cols <= got_cols

    def test_one_shot_write(self, tmp_path):
        tp_df = _make_df(7, n_events=10)
        out_path = tmp_path / "one_shot.root"

        writer = NtupleWriter(out_path, key_columns=["run", "lumi", "event"])
        writer.write(tp_df, tree_name="TrigPrim")
        writer.close()

        with uproot.open(out_path) as f:
            tree = f["TrigPrim"]
            n_events_expected = tp_df["event"].nunique()
            print(f"\none-shot write num_entries: {tree.num_entries}, expected: {n_events_expected}")
            assert tree.num_entries == n_events_expected

    def test_missing_key_column_raises(self, tmp_path):
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        out_path = tmp_path / "bad.root"
        writer = NtupleWriter(out_path, key_columns=["run", "event"])
        try:
            with pytest.raises(ValueError):
                writer.write(df)
        finally:
            writer.close()
