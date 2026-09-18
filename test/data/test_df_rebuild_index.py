import pandas as pd

from dunetrg.data.workspace import rebuild_dataframe_entry_index


class TestRebuildDataframeEntryIndex:
    def test_entry_subentry_assignment(self):
        # 3 hits in event_uid=100, 2 in 101, 1 in 102
        df = pd.DataFrame({
            "event_uid": [100, 100, 100, 101, 101, 102],
            "hit_x": [0.1, 0.2, 0.3, 1.1, 1.2, 2.1],
        })
        out = rebuild_dataframe_entry_index(df, ["event_uid"])
        entries = out.index.get_level_values("entry").tolist()
        subentries = out.index.get_level_values("subentry").tolist()
        expected_entries = [0, 0, 0, 1, 1, 2]
        expected_subentries = [0, 1, 2, 0, 1, 0]
        print(f"\nentries: {entries}, expected: {expected_entries}")
        assert entries == expected_entries
        print(f"subentries: {subentries}, expected: {expected_subentries}")
        assert subentries == expected_subentries

    def test_index_names(self):
        df = pd.DataFrame({"k": [1, 1, 2]})
        out = rebuild_dataframe_entry_index(df, ["k"])
        names = list(out.index.names)
        print(f"\nindex names: {names}, expected: ['entry', 'subentry']")
        assert names == ["entry", "subentry"]

    def test_multi_column_keys(self):
        # entry defined by the combination of (run, event)
        df = pd.DataFrame({
            "run": [1, 1, 1, 1],
            "event": [0, 0, 1, 1],
            "hit": [10, 20, 30, 40],
        })
        out = rebuild_dataframe_entry_index(df, ["run", "event"])
        entries = out.index.get_level_values("entry").tolist()
        expected_entries = [0, 0, 1, 1]
        print(f"\nentries (multi-column key): {entries}, expected: {expected_entries}")
        assert entries == expected_entries

    def test_mutates_and_returns_same_dataframe(self):
        df = pd.DataFrame({"k": [5, 5, 6]})
        out = rebuild_dataframe_entry_index(df, ["k"])
        print(f"\nout is df: {out is df}, expected: True")
        assert out is df
