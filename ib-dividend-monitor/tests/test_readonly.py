"""Garantías de solo lectura: ningún código del paquete puede operar."""

import re
from pathlib import Path

import pytest

from divmon.sources.ib_gateway import ALLOWED_METHODS, ReadOnlyIB, ReadOnlyViolation

SRC = Path(__file__).parents[1] / "src" / "divmon"
# Métodos de ib_async / TWS API (y del conector de IBKR) que crean, modifican o cancelan órdenes.
FORBIDDEN = [
    "place" + "Order", "cancel" + "Order", "reqGlobal" + "Cancel", "exercise" + "Options",
    "bracket" + "Order", "oca" + "Group", "order" + "_instruction",
]


def test_no_order_methods_in_source():
    offenders = []
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for name in FORBIDDEN:
            if re.search(name, text, re.IGNORECASE):
                offenders.append(f"{path.name}: {name}")
    assert offenders == []


def test_allowlist_is_read_only():
    assert not any(re.search("order|cancel|exercise", m, re.IGNORECASE) for m in ALLOWED_METHODS)


def test_wrapper_blocks_everything_else():
    ib = object.__new__(ReadOnlyIB)
    ib.__dict__["_ib"] = object()
    with pytest.raises(ReadOnlyViolation):
        getattr(ib, "place" + "Order")
    with pytest.raises(ReadOnlyViolation):
        ib.reqMktData
