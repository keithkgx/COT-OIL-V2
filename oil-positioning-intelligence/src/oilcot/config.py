"""Source and market registry. ICE is deliberately disabled pending authorized access."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Market:
    key: str
    label: str
    source: str
    code: str
    units: str
    enabled: bool = True

MARKETS = {
    "WTI": Market("WTI", "NYMEX WTI Crude", "CFTC", "067651", "1,000 bbl/contract"),
    "ULSD": Market("ULSD", "NYMEX ULSD / Heating Oil", "CFTC", "022651", "42,000 gal/contract"),
    "RBOB": Market("RBOB", "NYMEX RBOB Gasoline", "CFTC", "111659", "42,000 gal/contract"),
    "BRENT": Market("BRENT", "ICE Brent Crude", "ICE", "B", "1,000 bbl/contract", False),
    "GASOIL": Market("GASOIL", "ICE Low Sulphur Gasoil", "ICE", "G", "100 mt/contract", False),
}
DATASETS = {
    "combined": "kh3c-gbw2",
    "futures": "72hh-3qpy",
}
GROUPS = {
    "Managed Money": "m_money",
    "Producer/Merchant": "prod_merc",
    "Swap Dealers": "swap",
    "Other Reportables": "other_rept",
}
# Some PRE endpoints abbreviate a few "_all" field names; documented aliases below.
COLUMNS = {
    "Managed Money": {
        "long": ("m_money_positions_long_all",),
        "short": ("m_money_positions_short_all",),
        "spread": ("m_money_positions_spread_all",),
    },
    "Producer/Merchant": {
        "long": ("prod_merc_positions_long", "prod_merc_positions_long_all"),
        "short": ("prod_merc_positions_short", "prod_merc_positions_short_all"),
        "spread": (),  # No separate producer spreading column in disaggregated report.
    },
    "Swap Dealers": {
        "long": ("swap_positions_long_all",),
        "short": ("swap__positions_short_all", "swap_positions_short_all"),
        "spread": ("swap__positions_spread_all", "swap_positions_spread_all"),
    },
    "Other Reportables": {
        "long": ("other_rept_positions_long_all",),
        "short": ("other_rept_positions_short_all",),
        "spread": ("other_rept_positions_spread_all",),
    },
}
