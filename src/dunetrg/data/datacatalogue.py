import os
from pathlib import Path
import logging
import yaml
from typing import Optional, List, Union
from pydantic import BaseModel, field_validator
import dunetrg.data.workspace as workspace

from dunetrg.data.utils import temporary_log_level
from rich import print

_log = logging.getLogger(__name__)

#: Environment variable that points at the data root: the directory that
#: relative ``dataset_dir`` arguments are resolved against.
TPV_DATA_ROOT_ENV = "TPV_DATA_ROOT"


class DatasetEntry(BaseModel):
    trg_file: str
    rawadc_file: Optional[str] = None
    label: Optional[str] = None
    first_entry: Optional[int] = None
    last_entry: Optional[int] = None



class DataCatalogue(BaseModel):
    dataset_path: str
    dataset_info: dict
    datasets_spec: dict[str, DatasetEntry]
    tp_cut: Optional[str] = None
    tp_info_update: Optional[dict] = None

    @field_validator("datasets_spec")
    @classmethod
    def datasets_spec_not_empty(cls, v):
        if not v:
            raise ValueError("datasets_spec must not be empty")
        return v

def _resolve_dir(dataset_dir: Union[str, Path], data_root: Optional[Union[str, Path]] = None) -> Path:
    """Resolve *dataset_dir* to an absolute, existing directory.

    Absolute paths are used as-is. Relative paths are resolved against
    *data_root* if given, otherwise against the ``TPV_DATA_ROOT`` environment
    variable (the directory that is ``tpvalidator/data/`` today).
    """
    p = Path(dataset_dir)
    if not p.is_absolute():
        root = data_root if data_root is not None else os.environ.get(TPV_DATA_ROOT_ENV)
        if root is None:
            raise RuntimeError(
                f"Dataset directory '{dataset_dir}' is relative, but no data root is set. "
                f"Set the '{TPV_DATA_ROOT_ENV}' environment variable, or pass data_root= explicitly."
            )
        p = Path(root) / p
    if not p.exists():
        raise FileNotFoundError(f"Dataset directory '{p}' does not exist")
    if not p.is_dir():
        raise NotADirectoryError(f"'{p}' is not a directory")
    return p


def parse(dataset_dir: str, data_root: Optional[Union[str, Path]] = None) -> DataCatalogue:
    """Find and parse the datacatalogue.yaml in *dataset_dir*, return a DataCatalogue.

    If *dataset_dir* is relative, it is resolved against *data_root* if given,
    otherwise against the ``TPV_DATA_ROOT`` environment variable.
    """
    d = _resolve_dir(dataset_dir, data_root)
    cfg_file = d / "datacatalogue.yaml"
    if not cfg_file.exists():
        raise FileNotFoundError(f"Configuration file '{cfg_file}' does not exist")
    if not cfg_file.is_file():
        raise ValueError(f"'{cfg_file}' is not a regular file")
    try:
        with open(cfg_file) as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse '{cfg_file}': {e}")
    return DataCatalogue.model_validate(raw)


def list_datasets(dataset_dir: str, data_root: Optional[Union[str, Path]] = None) -> List[str]:
    """Return the names of datasets declared in the catalogue."""
    return list(parse(dataset_dir, data_root).datasets_spec.keys())


def get_workspace_args(dataset_dir: str, selection: Optional[List[str]] = None, data_root: Optional[Union[str, Path]] = None) -> dict:
    """Parse the catalogue and return constructor kwargs for each dataset's TriggerPrimitivesWorkspace.

    Returns a dict mapping dataset name to a dict with keys:
      ``trg_file``, ``rawadc_file`` (resolved Path or None), ``first_entry``,
      ``last_entry``, and ``dataset_info``.
    """
    d = _resolve_dir(dataset_dir, data_root)
    cfg = parse(dataset_dir, data_root)
    dataset_path = d / cfg.dataset_path
    result = {}
    for name, entry in cfg.datasets_spec.items():
        if selection and name not in selection:
            continue
        result[name] = dict(
            trg_file=dataset_path / entry.trg_file,
            rawadc_file=dataset_path / entry.rawadc_file if entry.rawadc_file else None,
            first_entry=entry.first_entry,
            last_entry=entry.last_entry,
            dataset_info=cfg.dataset_info,
        )
    return result


def load_datasets(dataset_dir: str, load_rawadc:bool=True, selection: Optional[List[str]] = None, data_root: Optional[Union[str, Path]] = None) -> dict:
    """Load workspace objects for each dataset (optionally filtered by *selection*)."""
    cfg = parse(dataset_dir, data_root)
    datasets = {}
    for name, args in get_workspace_args(dataset_dir, selection=selection, data_root=data_root).items():
        print(f"Loading {name}")
        ws = workspace.TriggerPrimitivesWorkspace(
            args['trg_file'],
            first_entry=args['first_entry'],
            last_entry=args['last_entry'],
            dataset_info=args['dataset_info'],
            rawadc_file=args['rawadc_file'] if load_rawadc else None,
        )
        print(f"Dataset '{name}': {ws.num_entries} events")
        print(ws.info)
        datasets[name] = ws

    if cfg.tp_cut:
        print('[yellow]Deprecation warning[/yellow]')
        for ws in datasets.values():
            ws.tps.query(cfg.tp_cut, inplace=True)

    if cfg.tp_info_update:
        for ws in datasets.values():
            ws.tps._info.update(cfg.tp_info_update)

    return datasets


def load(dataset_dir: str, selection: Optional[List[str]] = None, load_rawadc:bool=True, data_root: Optional[Union[str, Path]] = None) -> dict:
    """Load all datasets from a catalogue directory (convenience wrapper)."""
    return load_datasets(dataset_dir, load_rawadc, selection, data_root=data_root)


def iterdataset_xp(dataset_dir, dataset_name, num_entries, load_rawadc:bool=False, data_root: Optional[Union[str, Path]] = None):

    d = _resolve_dir(dataset_dir, data_root)
    cfg = parse(dataset_dir, data_root)
    print(cfg)
    dataset_path = d / cfg.dataset_path
    if dataset_name not in cfg.datasets_spec:
        raise KeyError(f'Dataset {dataset_name} not found in {dataset_dir}')

    dataset = cfg.datasets_spec[dataset_name]
    ws = workspace.TriggerPrimitivesWorkspace(dataset_path / dataset.trg_file)

    total_num_entries = ws.num_entries
    del ws
    print(f"Found {total_num_entries} entries")

    first_entry = dataset.first_entry if dataset.first_entry is not None else 0
    last_entry = dataset.last_entry if dataset.last_entry is not None else total_num_entries

    for i in range(first_entry, last_entry, num_entries):
        print(i, i+num_entries)
        yield workspace.TriggerPrimitivesWorkspace(dataset_path / dataset.trg_file, first_entry=i, last_entry=i+num_entries)
    return None
