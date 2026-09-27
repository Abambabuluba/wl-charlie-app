from datetime import datetime, timedelta

from divmon.alerts import Alert, EmailNotifier, TelegramNotifier, _chunks, dispatch, margin_alerts
from divmon.analytics.margin import compute_margin
from divmon.storage import Store


class Collect:
    def __init__(self):
        self.sent = []

    def send(self, text):
        self.sent.append(text)

    def send_report(self, summary, path, subject):
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


class FakeSMTP:
    sent = []

    def __init__(self, host, port, timeout=None):
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def login(self, user, password):
        self.user = user

    def send_message(self, msg):
        FakeSMTP.sent.append(msg)


def test_email_alerts_and_report(tmp_path):
    FakeSMTP.sent = []
    mail = EmailNotifier("smtp.gmail.com", 465, "yo@gmail.com", "app-pass", "destino@gmail.com", smtp_factory=FakeSMTP)
    store = Store(":memory:")
    dispatch([Alert("a", "crítico", "Colchón <25 %"), Alert("b", "aviso", "KSPI pesa 77 %")], store, mail, 72)
    msg = FakeSMTP.sent[0]
    assert msg["Subject"] == "🔴 Cartera IBKR: 2 avisos"
    assert msg["To"] == "destino@gmail.com"
    assert "Colchón <25 %" in msg.get_body(("plain",)).get_content()
    assert "&lt;25" in msg.get_body(("html",)).get_content()

    report = tmp_path / "informe.html"
    report.write_text("<html>ok</html>", encoding="utf-8")
    mail.send_report("Resumen", report, "Informe semanal")
    msg = FakeSMTP.sent[1]
    assert msg["Subject"] == "Informe semanal"
    (att,) = list(msg.iter_attachments())
    assert att.get_filename() == "informe.html"
