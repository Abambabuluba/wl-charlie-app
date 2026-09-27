from datetime import datetime, timedelta

from divmon.alerts import Alert, TelegramNotifier, _chunks, dispatch, margin_alerts
from divmon.analytics.margin import compute_margin
from divmon.storage import Store


class Collect:
    def __init__(self):
        self.sent = []

    def send(self, text):
        self.sent.append(text)

    def send_file(self, path, caption=""):
        self.sent.append(path)


def test_dispatch_respects_cooldown():
    store, out = Store(":memory:"), Collect()
    alerts = [Alert("a", "aviso", "uno"), Alert("b", "crítico", "dos <b>")]
    now = datetime(2026, 9, 27, 8, 0)
    assert len(dispatch(alerts, store, out, 72, now=now)) == 2
    assert out.sent[0].index("dos") < out.sent[0].index("uno"), "los críticos van primero"
    assert "&lt;b&gt;" in out.sent[0], "el texto se escapa para Telegram"
    assert dispatch(alerts, store, out, 72, now=now + timedelta(hours=10)) == []
    assert len(dispatch(alerts, store, out, 72, now=now + timedelta(hours=73))) == 2
    assert len(out.sent) == 2


def test_margin_alert_thresholds(stmt, cfg):
    m = compute_margin(stmt, cfg)
    assert margin_alerts(m, cfg) == []
    cfg.margin.alerts.loan_to_value_max = 0.2
    cfg.margin.alerts.drop_to_call_min = 0.9
    keys = {a.key: a.severity for a in margin_alerts(m, cfg)}
    assert keys == {"margin:ltv": "aviso", "margin:drop": "aviso"}


def test_chunks_split_long_messages():
    text = "\n".join("x" * 100 for _ in range(100))
    parts = _chunks(text, 1000)
    assert all(len(p) <= 1000 for p in parts)
    assert "".join(parts) == text


def test_telegram_notifier_posts_html():
    calls = []

    class Resp:
        status_code = 200

        def json(self):
            return {"ok": True}

    class Session:
        def post(self, url, data=None, files=None, timeout=None):
            calls.append((url, data))
            return Resp()

    TelegramNotifier("TOKEN", "42", session=Session()).send("hola")
    url, data = calls[0]
    assert url == "https://api.telegram.org/botTOKEN/sendMessage"
    assert data["chat_id"] == "42" and data["parse_mode"] == "HTML"
