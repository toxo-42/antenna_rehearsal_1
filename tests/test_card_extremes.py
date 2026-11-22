"""Any sweep that passes the input check is judged without errors and without inf/nan text."""

import random
import re
from dataclasses import asdict

import pytest

from src.models import Antenna, AntennaKind, CalMode, Sweep
from src.sweep_parser import check_sweep
from src.verdict import build_card

NON_FINITE = re.compile(r"(?<![a-z])(inf|nan)(?![a-z])", re.IGNORECASE)
EXTREME_DB = [1000.0, -1000.0, 0.0, -10.0, -6.0, -3.0, -30.0, 999.9]
EXTREME_GAMMA = [1 + 0j, 1 + 5e-324j, 1 - 1e-300j, 1000 + 1000j, -1000 + 0j, 0j, 0.5 + 0.5j]


def random_sweep(rng: random.Random) -> Sweep:
    count = rng.randint(3, 30)
    low = rng.choice([1e-6, 1e-3, 1.0, 400.0])
    high = rng.choice([low * 1.0001, low * 3, 1e6])
    f_mhz = tuple(sorted({rng.uniform(low, high) for _ in range(count)} | {low, high}))
    s11_db = tuple(rng.choice(EXTREME_DB) for _ in f_mhz)
    gamma = tuple(rng.choice(EXTREME_GAMMA) for _ in f_mhz) if rng.random() < 0.7 else None
    return Sweep(f_mhz=f_mhz, s11_db=s11_db, gamma=gamma)


def card_texts(card: object) -> list[str]:
    data = asdict(card)  # type: ignore[call-overload]
    texts = [data["headline"], *data["status"]]
    return texts + [value for d in data["diagnoses"] for value in d.values()]


@pytest.mark.parametrize("seed", range(300))
def test_allowed_sweep_gives_a_clean_card(seed: int) -> None:
    rng = random.Random(seed)
    sweep = random_sweep(rng)
    check_sweep(sweep)
    target = rng.choice(
        [sweep.f_mhz[0], sweep.f_mhz[-1], rng.uniform(sweep.f_mhz[0], sweep.f_mhz[-1])]
    )
    antenna = Antenna(name="a", kind=rng.choice(list(AntennaKind)), target_mhz=target)

    card = build_card(sweep, antenna, rng.choice(list(CalMode)))

    assert [t for t in card_texts(card) if NON_FINITE.search(t)] == []


def test_third_mode_with_the_lowest_allowed_frequency() -> None:
    f_mhz = (1e-6, 2e-6, 3e-6, 4e-6, 5e-6, 6e-6, 7e-6)
    sweep = Sweep(f_mhz=f_mhz, s11_db=(-1.0, -20.0, -1.0, -1.0, -1.0, -20.0, -1.0))
    check_sweep(sweep)

    card = build_card(sweep, Antenna("a", AntennaKind.MONOPOLE, 6e-6), CalMode.VNA)

    assert [t for t in card_texts(card) if NON_FINITE.search(t)] == []
