from datetime import date

import pytest

from divmon.models import DIVIDEND_TYPES
from divmon.sources import flex


def test_parse_positions_skip_lots(stmt):
    assert stmt.account_id == "U1234567"
    assert stmt.report_date == date(2026, 9, 25)
    assert sorted(p.symbol for p in stmt.positions) == ["ALV", "BATS", "ENG", "MO", "O", "SAN"]
    san = next(p for p in stmt.positions if p.symbol == "SAN")
    assert san.quantity == 3000 and san.value_base == pytest.approx(25500)
    assert san.issuer_country == "ES" and san.listing_exchange == "BM"
    mo = next(p for p in stmt.positions if p.symbol == "MO")
    assert mo.value_base == pytest.approx(17400 * 0.9)


def test_parse_cash_and_fx(stmt):
    assert {c.currency: c.ending_cash for c in stmt.cash} == {"EUR": -25000, "USD": 300}
    # Se queda con el tipo de cambio más reciente y solo los que van hacia la divisa base.
    assert stmt.fx_to_base == {"EUR": 1.0, "USD": 0.9, "GBP": 1.18}


def test_parse_transactions(stmt):
    types = {t.type for t in stmt.transactions}
    assert {"Dividends", "Withholding Tax", "Broker Interest Paid", "Deposits/Withdrawals"} <= types
    assert all(t.description != "resumen" for t in stmt.transactions), "las filas SUMMARY se descartan"
    san = [t for t in stmt.transactions if t.symbol == "SAN" and t.type in DIVIDEND_TYPES]
    assert [t.per_share for t in san] == [0.095, 0.10, 0.11]
    assert len({t.transaction_id for t in stmt.transactions}) == len(stmt.transactions)


def test_parse_accruals(stmt):
    (a,) = stmt.accruals
    assert (a.symbol, a.pay_date, a.net_amount) == ("MO", date(2026, 10, 10), 270.3)


@pytest.mark.parametrize("raw, expected", [
    ("20260115", date(2026, 1, 15)),
    ("2026-01-15", date(2026, 1, 15)),
    ("20260115;093000", date(2026, 1, 15)),
    ("2026-01-15, 09:30:00", date(2026, 1, 15)),
    ("", None),
])
def test_dates(raw, expected):
    assert flex._date(raw) == expected


def test_unsupported_date_format():
    with pytest.raises(ValueError, match="yyyyMMdd"):
        flex._date("01/15/2026")


class FakeResponse:
    def __init__(self, text):
        self.content = text.encode()

    def raise_for_status(self):
        pass


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, params))
        return FakeResponse(self.responses.pop(0))


SEND_OK = ("<FlexStatementResponse><Status>Success</Status><ReferenceCode>123</ReferenceCode>"
           "<Url>https://example.test/GetStatement</Url></FlexStatementResponse>")


def test_fetch_retries_while_generating():
    session = FakeSession([
        SEND_OK,
        "<FlexStatementResponse><Status>Warn</Status><ErrorCode>1019</ErrorCode>"
        "<ErrorMessage>Statement generation in progress.</ErrorMessage></FlexStatementResponse>",
        "<FlexQueryResponse><FlexStatements/></FlexQueryResponse>",
    ])
    sleeps = []
    xml = flex.fetch_statement_xml("tok", "q1", session=session, sleep=sleeps.append)
    assert xml.startswith(b"<FlexQueryResponse")
    assert sleeps == [5]
    assert session.calls[0][1] == {"t": "tok", "q": "q1", "v": "3"}
    assert session.calls[1][1]["q"] == "123"


def test_fetch_expired_token_has_hint():
    session = FakeSession([
        "<FlexStatementResponse><Status>Fail</Status><ErrorCode>1012</ErrorCode>"
        "<ErrorMessage>Token has expired.</ErrorMessage></FlexStatementResponse>",
    ])
    with pytest.raises(flex.FlexError, match="caducado"):
        flex.fetch_statement_xml("tok", "q1", session=session, sleep=lambda s: None)
