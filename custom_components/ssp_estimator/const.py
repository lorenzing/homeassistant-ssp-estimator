"""Constants for the SSP estimate helper."""

DOMAIN = "ssp_estimator"
IMPORT = "import_energy"
EXPORT = "export_energy"
RATES = ("pun_average", "zonal_average", "cusf")
ZONES = ("NORD", "CNOR", "CSUD", "SUD", "CALA", "SICI", "SARD")
ESTIMATE_STATUSES = (
    "reference_year_outdated", "annual_counters_required", "energy_unavailable",
    "counter_paused", "periods_do_not_match", "rates_required",
    "rate_reference_required", "invalid_rates", "partial_year_estimate", "annual_estimate",
)
