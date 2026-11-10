"""Pure, dependency-free annual SSP scenario calculation; no GSE account access."""

from dataclasses import dataclass
from math import isfinite


def number(value: object) -> float:
    """Accept finite numeric inputs, excluding boolean pseudo-numbers."""
    if isinstance(value, bool):
        raise ValueError("A boolean is not a measured value")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as err:
        raise ValueError("Missing or invalid number") from err
    if not isfinite(result):
        raise ValueError("A finite value is required")
    return result


def energy_kwh(value: object, unit: str | None) -> float:
    """Convert energy only: never silently interpret power or unknown units."""
    factors = {"Wh": 0.001, "kWh": 1.0, "MWh": 1000.0}
    if unit not in factors:
        raise ValueError("Energy must be expressed in Wh, kWh or MWh")
    result = number(value) * factors[unit]
    if result < 0:
        raise ValueError("Imported and exported energy must be non-negative")
    return result


@dataclass(frozen=True)
class Estimate:
    """Annual, gross scenario amounts, before administrative fees/taxes."""

    imported_kwh: float
    exported_kwh: float
    exchanged_kwh: float
    oe: float
    cei: float
    energy_component: float
    services_component: float
    contribution: float
    economic_surplus: float


def estimate(imported: float, exported: float, pun: float, zonal: float, cusf: float) -> Estimate:
    """Compute min(OE, CEI) + CUSf * min(Ep, Ei).

    Prices are energy-weighted averages in EUR/kWh for the SAME annual
    observation period. These are scenario assumptions, not current SEN
    purchase prices. CEI and OE use separate import/export weighted averages.
    Economic surplus is EUR, not a surplus of physical kWh.
    """
    imported, exported, pun, zonal, cusf = map(number, (imported, exported, pun, zonal, cusf))
    if min(imported, exported, cusf) < 0:
        raise ValueError("Energy and CUSf cannot be negative")
    exchanged = min(imported, exported)
    oe = imported * pun
    cei = exported * zonal
    energy_component = min(oe, cei)
    services = exchanged * cusf
    values = (oe, cei, energy_component, services, energy_component + services, max(cei - oe, 0.0))
    if not all(isfinite(value) for value in values):
        raise ValueError("Calculation overflow")
    return Estimate(imported, exported, exchanged, *values)
