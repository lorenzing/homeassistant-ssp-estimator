"""Build identical strings.json and English/Italian config flow translations."""

import json
from pathlib import Path

root = Path(__file__).parents[1] / "custom_components/ssp_estimator"
for language, title, fields, errors, description in (
    ("it", "Stima Scambio sul Posto", {
        "name": "Nome", "import_energy": "Contatore ANNUALE energia prelevata",
        "export_energy": "Contatore ANNUALE energia immessa", "zone": "Zona di mercato",
        "reference_year": "Anno di riferimento", "pun_average": "PUN medio ponderato sui prelievi (€/kWh)",
        "zonal_average": "Prezzo zonale medio ponderato sulle immissioni (€/kWh)",
        "cusf": "CUSf di riferimento (€/kWh)", "rate_reference": "Fonte, periodo e ipotesi dei parametri",
    }, {"same_sensor": "Scegli due contatori distinti.", "invalid_energy": "Scegli un sensore disponibile con energia in Wh, kWh o MWh."},
     "Scegli due Utility Meter annuali dello stesso periodo. I parametri economici sono facoltativi: se sconosciuti, gli importi resteranno indisponibili. Si tratta di una stima, non del conguaglio GSE."),
    ("en", "Scambio sul Posto estimate", {
        "name": "Name", "import_energy": "YEARLY imported energy counter",
        "export_energy": "YEARLY exported energy counter", "zone": "Market zone",
        "reference_year": "Reference year", "pun_average": "Import-weighted PUN average (EUR/kWh)",
        "zonal_average": "Export-weighted zonal price average (EUR/kWh)",
        "cusf": "Reference CUSf (EUR/kWh)", "rate_reference": "Parameter source, period and assumptions",
    }, {"same_sensor": "Choose two distinct energy counters.", "invalid_energy": "Choose an available Wh, kWh or MWh energy sensor."},
     "Choose two yearly Utility Meter helpers for the same period. Financial assumptions are optional: leave unknown values empty. This is an estimate, not the official GSE settlement."),
):
    value = {"title": title, "config": {"step": {"user": {"title": title, "description": description, "data": fields}}, "error": errors},
             "options": {"step": {"init": {"title": title, "description": description, "data": {key: text for key, text in fields.items() if key not in ("name", "import_energy", "export_energy")}}}}}
    path = root / "translations" / f"{language}.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if language == "en":
        (root / "strings.json").write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
