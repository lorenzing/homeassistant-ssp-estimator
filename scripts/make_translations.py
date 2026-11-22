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
    errors.update({
        "invalid_province": "Scegli una provincia dall'elenco." if language == "it" else "Choose a province from the list.",
        "annual_counters_required": "Scegli un Utility Meter annuale senza fasce e senza consumo netto, con periodo valido nell'anno corrente." if language == "it" else "Choose a yearly Utility Meter without tariffs or net consumption and with a valid current-year period.",
        "counter_paused": "Il contatore è in pausa. Riprendi il conteggio prima di configurare la stima." if language == "it" else "The counter is paused. Resume collection before configuring the estimate.",
        "periods_do_not_match": "I due contatori devono coprire lo stesso periodo (tolleranza di cinque minuti)." if language == "it" else "Both counters must cover the same period (five-minute tolerance).",
    })
    fields.pop("zone")
    fields["province"] = "Provincia dell'impianto (zona di mercato automatica)" if language == "it" else "Installation province (automatic market zone)"
    description += " La zona di mercato è determinata dalla provincia selezionata." if language == "it" else " The market zone is determined by the selected province."
    value = {"title": title, "config": {"step": {"user": {"title": title, "description": description, "data": fields}}, "error": errors},
             "options": {"step": {"init": {"title": title, "description": description, "data": {key: text for key, text in fields.items() if key not in ("name", "import_energy", "export_energy")}}}, "error": errors}}
    states = {
        "reference_year_outdated": ("Parametri da aggiornare per l'anno corrente", "Update assumptions for the current year"),
        "annual_counters_required": ("Servono contatori annuali validi", "Valid annual counters required"),
        "energy_unavailable": ("Dati di energia non disponibili", "Energy data unavailable"),
        "counter_paused": ("Contatore in pausa", "Counter paused"),
        "periods_do_not_match": ("Periodi dei contatori non allineati", "Counter periods do not match"),
        "rates_required": ("In attesa di prezzi medi e CUSf", "Average prices and CUSf required"),
        "rate_reference_required": ("Indicare fonte e periodo dei parametri", "Parameter source and period required"),
        "invalid_rates": ("Parametri economici non validi", "Invalid financial assumptions"),
        "partial_year_estimate": ("Stima su periodo parziale", "Partial-year estimate"),
        "annual_estimate": ("Stima annuale", "Annual estimate"),
    }
    value["entity"] = {"sensor": {"estimate_status": {"state": {
        key: labels[0 if language == "it" else 1] for key, labels in states.items()
    }}}}
    path = root / "translations" / f"{language}.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if language == "en":
        (root / "strings.json").write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
