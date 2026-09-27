from pathlib import Path

import pytest

from divmon.config import config_from_dict
from divmon.sources.flex import parse_statement

FIXTURE = Path(__file__).parent / "fixtures" / "flex_sample.xml"


def base_config(tmp_path: Path, **overrides):
    raw = {
        "base_currency": "EUR",
        "data_dir": str(tmp_path / "data"),
        "fundamentals": {"provider": "none"},
        "criteria": {"per_max": 15, "dividend_yield_min": 0.045, "payout_max": 0.8, "debt_ebitda_max": 3.5},
        "margin": {"interest_rates": {"EUR": 0.045, "USD": 0.06}, "maintenance_rate_default": 0.25},
        "amortization": {"monthly_contribution": 500, "dividends_to_debt": True, "dividend_growth": 0.0},
        "radar": {"candidates": [{"symbol": "VZ"}]},
        "symbols": {
            "ENG": {"per": 14, "payout": 0.95, "debt_ebitda": 4.8, "sector": "Utilities"},
            "MO": {"per": 9, "payout": 0.78, "debt_ebitda": 2.3},
            "VZ": {"per": 9.5, "dividend_yield": 0.064, "payout": 0.6, "debt_ebitda": 2.6},
        },
        "alerts": {"channel": "console", "cooldown_hours": 72},
    }
    raw.update(overrides)
    return config_from_dict(raw)


@pytest.fixture
def cfg(tmp_path):
    return base_config(tmp_path)


@pytest.fixture
def stmt():
    return parse_statement(FIXTURE.read_bytes(), "EUR")
