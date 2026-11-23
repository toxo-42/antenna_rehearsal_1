"""Shared value types and thresholds for the verdict core. No logic beyond simple derived values."""

from dataclasses import dataclass
from enum import StrEnum

from src.tolerance import at_least, at_most

MATCH_THRESHOLD_DB = -10.0
RESONANCE_MIN_DEPTH_DB = 3.0
RESONANCE_MAX_S11_DB = -6.0
WEAK_DIP_MIN_DEPTH_DB = 2.0
CANDIDATE_WINDOW_PCT = 20.0
# A shallow resonance this far from the target is a length problem first (provisional value).
LENGTH_FIRST_PCT = 5.0
# A monopole resonates again near three times its base frequency (measured: 2.75 to 3.17).
THIRD_MODE_MIN_RATIO = 2.6
THIRD_MODE_MAX_RATIO = 3.4
# ... and near five times it (measured: 4.82 to 5.01).
FIFTH_MODE_MIN_RATIO = 4.5
FIFTH_MODE_MAX_RATIO = 5.5
# Fewer measurement steps than this across a resonance: its frequency and depth are unsure.
MIN_STEPS_ACROSS_RESONANCE = 5.0
# The range suggested for measuring again: this far to each side of the resonance.
REMEASURE_SPAN_PCT = 20.0
REFERENCE_OHM = 50.0
LOW_FREQ_FRACTION = 0.1
# S11 above this is a bad measurement. Calibrated readings reach about +0.02 dB and USB
# readings +0.07 dB near 0 dB, while a broken calibration goes past +1 dB.
POSITIVE_S11_DB = 0.2


class AntennaKind(StrEnum):
    MONOPOLE = "monopole"
    PATCH = "patch"


class Stage(StrEnum):
    NONE = "none"
    UNMATCHED = "unmatched"
    OFFTARGET = "offtarget"
    NARROW = "narrow"
    GOOD = "good"


class CalMode(StrEnum):
    VNA = "vna"
    UNKNOWN = "unknown"


class CardStage(StrEnum):
    """Stage shown on the card: the p1 stages plus `invalid` for a sweep that cannot be judged."""

    NONE = "none"
    UNMATCHED = "unmatched"
    OFFTARGET = "offtarget"
    NARROW = "narrow"
    GOOD = "good"
    INVALID = "invalid"


TYPICAL_BANDWIDTH_PCT: dict[AntennaKind, float] = {
    AntennaKind.MONOPOLE: 8.0,
    AntennaKind.PATCH: 2.5,
}


@dataclass(frozen=True)
class Antenna:
    name: str
    kind: AntennaKind
    target_mhz: float


@dataclass(frozen=True)
class Sweep:
    """One S11 sweep. `gamma` is the complex reflection coefficient when the source has it."""

    f_mhz: tuple[float, ...]
    s11_db: tuple[float, ...]
    gamma: tuple[complex, ...] | None = None


@dataclass(frozen=True)
class Band:
    low_mhz: float
    high_mhz: float

    @property
    def width_mhz(self) -> float:
        return self.high_mhz - self.low_mhz

    def contains(self, f_mhz: float) -> bool:
        return at_least(f_mhz, self.low_mhz) and at_most(f_mhz, self.high_mhz)


@dataclass(frozen=True)
class Dip:
    """A local minimum of S11 with its depth (prominence)."""

    index: int
    f_mhz: float
    s11_db: float
    depth_db: float


@dataclass(frozen=True)
class Resonance(Dip):
    band: Band | None = None

    @property
    def bandwidth_pct(self) -> float | None:
        if self.band is None:
            return None
        return self.band.width_mhz / self.f_mhz * 100


@dataclass(frozen=True)
class ResonanceScan:
    resonances: tuple[Resonance, ...]
    weak_dips: tuple[Dip, ...]
    minor_count: int


@dataclass(frozen=True)
class Impedance:
    r_ohm: float
    x_ohm: float


@dataclass(frozen=True)
class Classification:
    """Stage verdict. `others` are the unselected resonances, nearest to the target first.
    `weak_dips` are the dips too shallow to be resonances, in frequency order."""

    stage: Stage
    selected: Resonance | None
    offset_pct: float | None
    others: tuple[Resonance, ...]
    weak_dips: tuple[Dip, ...] = ()


@dataclass(frozen=True)
class RuleContext:
    """Everything a diagnosis rule may look at. Rules never see each other's results."""

    classification: Classification
    sweep: Sweep
    antenna: Antenna
    cal_mode: CalMode


@dataclass(frozen=True)
class Diagnosis:
    key: str
    title: str
    evidence: str
    action: str
    guide: str


@dataclass(frozen=True)
class Remeasure:
    """A narrower range to measure again, in whole MHz, and the sentence shown with it. Only a
    suggestion: the student presses measure."""

    start_mhz: int
    stop_mhz: int
    note: str


@dataclass(frozen=True)
class Card:
    """The verdict card. Field names match `card` in contract/measurement.json."""

    stage: CardStage
    headline: str
    status: tuple[str, ...]
    diagnoses: tuple[Diagnosis, ...]
    remeasure: Remeasure | None = None
