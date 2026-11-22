"""Where a sweep comes from. The verdict always uses the antenna stored in the database."""

from pathlib import Path
from typing import Protocol

from src import store
from src.models import Sweep
from src.synthetic import SAMPLE_NAMES, make_sample

SOURCE_VALUES = ("usb", "csv", "stored", "synthetic")


class SweepSource(Protocol):
    """A swappable sweep provider. `source` is one of SOURCE_VALUES."""

    source: str

    def read(self) -> Sweep: ...


class SyntheticSource:
    """A named synthetic sample. Raises KeyError for an unknown name."""

    source = "synthetic"

    def __init__(self, name: str) -> None:
        if name not in SAMPLE_NAMES:
            raise KeyError(name)
        self.name = name

    def read(self) -> Sweep:
        return make_sample(self.name).sweep


class StoredSource:
    """The sweep of a saved measurement, read again from the database."""

    source = "stored"

    def __init__(self, db_path: Path, measurement_id: int) -> None:
        self.db_path = db_path
        self.measurement_id = measurement_id

    def read(self) -> Sweep:
        with store.connect(self.db_path) as conn:
            row = store.get_measurement(conn, self.measurement_id)
        if row is None:
            raise LookupError(f"측정 {self.measurement_id}번이 없습니다.")
        return store.sweep_from_json(row["sweep_json"])
