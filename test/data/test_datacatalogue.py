import pytest

import dunetrg.data.datacatalogue as dctl


CATALOGUE_YAML = """
dataset_path: "raw"
dataset_info:
  detector: test
datasets_spec:
  ds1:
    trg_file: "trg.root"
    first_entry: 0
    last_entry: 10
"""


def _make_dataset_dir(base):
    """Create a minimal dataset directory with a fake datacatalogue.yaml under *base*."""
    d = base / "vd" / "1x8x14" / "preprod"
    d.mkdir(parents=True)
    (d / "datacatalogue.yaml").write_text(CATALOGUE_YAML)
    return d


class TestResolveDir:
    def test_absolute_path_without_data_root(self, tmp_path, monkeypatch):
        monkeypatch.delenv("TPV_DATA_ROOT", raising=False)
        d = _make_dataset_dir(tmp_path)
        got = dctl._resolve_dir(str(d))
        print(f"\n_resolve_dir(absolute path): {got}, expected: {d}")
        assert got == d

    def test_relative_path_uses_env_var(self, tmp_path, monkeypatch):
        d = _make_dataset_dir(tmp_path)
        monkeypatch.setenv("TPV_DATA_ROOT", str(tmp_path))
        got = dctl._resolve_dir("vd/1x8x14/preprod")
        print(f"\n_resolve_dir(relative, TPV_DATA_ROOT={tmp_path}): {got}, expected: {d}")
        assert got == d

    def test_relative_path_uses_data_root_arg(self, tmp_path, monkeypatch):
        monkeypatch.delenv("TPV_DATA_ROOT", raising=False)
        d = _make_dataset_dir(tmp_path)
        got = dctl._resolve_dir("vd/1x8x14/preprod", data_root=tmp_path)
        print(f"\n_resolve_dir(relative, data_root={tmp_path}): {got}, expected: {d}")
        assert got == d

    def test_data_root_arg_overrides_env_var(self, tmp_path, monkeypatch):
        d = _make_dataset_dir(tmp_path)
        monkeypatch.setenv("TPV_DATA_ROOT", str(tmp_path / "not_the_right_root"))
        got = dctl._resolve_dir("vd/1x8x14/preprod", data_root=tmp_path)
        print(f"\n_resolve_dir(data_root overrides env): {got}, expected: {d}")
        assert got == d

    def test_relative_path_raises_without_root(self, tmp_path, monkeypatch):
        monkeypatch.delenv("TPV_DATA_ROOT", raising=False)
        with pytest.raises(RuntimeError, match="TPV_DATA_ROOT"):
            dctl._resolve_dir("vd/1x8x14/preprod")

    def test_nonexistent_absolute_path_raises(self, tmp_path):
        missing = tmp_path / "does_not_exist"
        with pytest.raises(FileNotFoundError):
            dctl._resolve_dir(str(missing))


class TestParseAndListDatasets:
    def test_parse_returns_catalogue(self, tmp_path, monkeypatch):
        _make_dataset_dir(tmp_path)
        monkeypatch.setenv("TPV_DATA_ROOT", str(tmp_path))
        cat = dctl.parse("vd/1x8x14/preprod")
        print(f"\ncat.dataset_path: {cat.dataset_path!r}, expected: 'raw'")
        assert cat.dataset_path == "raw"
        print(f"datasets_spec keys: {list(cat.datasets_spec)}, expected: ['ds1']")
        assert list(cat.datasets_spec) == ["ds1"]

    def test_parse_with_data_root_arg(self, tmp_path, monkeypatch):
        monkeypatch.delenv("TPV_DATA_ROOT", raising=False)
        _make_dataset_dir(tmp_path)
        cat = dctl.parse("vd/1x8x14/preprod", data_root=tmp_path)
        print(f"\ncat.dataset_path (data_root arg): {cat.dataset_path!r}, expected: 'raw'")
        assert cat.dataset_path == "raw"

    def test_list_datasets(self, tmp_path, monkeypatch):
        _make_dataset_dir(tmp_path)
        monkeypatch.setenv("TPV_DATA_ROOT", str(tmp_path))
        names = dctl.list_datasets("vd/1x8x14/preprod")
        print(f"\nlist_datasets: {names}, expected: ['ds1']")
        assert names == ["ds1"]

    def test_get_workspace_args_resolves_paths(self, tmp_path, monkeypatch):
        d = _make_dataset_dir(tmp_path)
        monkeypatch.setenv("TPV_DATA_ROOT", str(tmp_path))
        args = dctl.get_workspace_args("vd/1x8x14/preprod")
        expected_trg = d / "raw" / "trg.root"
        print(f"\nargs['ds1']['trg_file']: {args['ds1']['trg_file']}, expected: {expected_trg}")
        assert args["ds1"]["trg_file"] == expected_trg
        print(f"args['ds1']['rawadc_file']: {args['ds1']['rawadc_file']}, expected: None")
        assert args["ds1"]["rawadc_file"] is None

    def test_get_workspace_args_with_data_root_arg(self, tmp_path, monkeypatch):
        monkeypatch.delenv("TPV_DATA_ROOT", raising=False)
        d = _make_dataset_dir(tmp_path)
        args = dctl.get_workspace_args("vd/1x8x14/preprod", data_root=tmp_path)
        expected_trg = d / "raw" / "trg.root"
        print(f"\nargs['ds1']['trg_file'] (data_root arg): {args['ds1']['trg_file']}, expected: {expected_trg}")
        assert args["ds1"]["trg_file"] == expected_trg
