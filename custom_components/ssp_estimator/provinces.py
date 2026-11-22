"""Italian provinces and geographical electricity market zones.

Territorial names: ISTAT, 2026 (including the Sardinian reorganisation).
Market areas: ARERA https://www.arera.it/fileadmin/allegati/eventi/230222Autoconsumo.pdf
"""

_BY_ZONE = {
    "NORD": (
        "Aosta", "Alessandria", "Asti", "Biella", "Cuneo", "Novara", "Torino",
        "Verbano-Cusio-Ossola", "Vercelli", "Genova", "Imperia", "La Spezia", "Savona",
        "Bergamo", "Brescia", "Como", "Cremona", "Lecco", "Lodi", "Mantova", "Milano",
        "Monza e della Brianza", "Pavia", "Sondrio", "Varese", "Bolzano", "Trento",
        "Belluno", "Padova", "Rovigo", "Treviso", "Venezia", "Verona", "Vicenza",
        "Gorizia", "Pordenone", "Trieste", "Udine", "Bologna", "Ferrara", "Forlì-Cesena",
        "Modena", "Parma", "Piacenza", "Ravenna", "Reggio nell'Emilia", "Rimini",
    ),
    "CNOR": (
        "Arezzo", "Firenze", "Grosseto", "Livorno", "Lucca", "Massa-Carrara", "Pisa",
        "Pistoia", "Prato", "Siena", "Ancona", "Ascoli Piceno", "Fermo", "Macerata",
        "Pesaro e Urbino",
    ),
    "CSUD": (
        "Perugia", "Terni", "Frosinone", "Latina", "Rieti", "Roma", "Viterbo",
        "Chieti", "L'Aquila", "Pescara", "Teramo", "Avellino", "Benevento", "Caserta",
        "Napoli", "Salerno",
    ),
    "SUD": (
        "Campobasso", "Isernia", "Bari", "Barletta-Andria-Trani", "Brindisi", "Foggia",
        "Lecce", "Taranto", "Matera", "Potenza",
    ),
    "CALA": ("Catanzaro", "Cosenza", "Crotone", "Reggio Calabria", "Vibo Valentia"),
    "SICI": (
        "Agrigento", "Caltanissetta", "Catania", "Enna", "Messina", "Palermo",
        "Ragusa", "Siracusa", "Trapani",
    ),
    "SARD": (
        "Cagliari", "Sassari", "Gallura Nord-Est Sardegna", "Nuoro", "Ogliastra",
        "Oristano", "Medio Campidano", "Sulcis Iglesiente",
    ),
}

PROVINCE_ZONES = {province: zone for zone, provinces in _BY_ZONE.items() for province in provinces}


def province_options():
    """Searchable dropdown labels show the selected market zone immediately."""
    return [{"value": name, "label": f"{name} · {PROVINCE_ZONES[name]}"}
            for name in sorted(PROVINCE_ZONES)]


def with_province_zone(config):
    """Derive the zone instead of trusting an unrelated submitted zone."""
    return {**config, "zone": PROVINCE_ZONES[config["province"]]}
