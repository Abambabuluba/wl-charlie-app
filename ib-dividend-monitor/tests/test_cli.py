import yaml

from divmon.cli import main
from divmon.storage import Store

from .conftest import FIXTURE, base_config


def write_config(tmp_path):
    cfg = {
        "data_dir": str(tmp_path / "data"),
        "fundamentals": {"provider": "none"},
        "news": {"enabled": False},
        "alerts": {"channel": "console", "cooldown_hours": 72},
        "radar": {"candidates": [{"symbol": "VZ"}]},
        "symbols": {"VZ": {"per": 9.5, "dividend_yield": 0.064, "payout": 0.6, "debt_ebitda": 2.6}},
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return str(path)


def run(tmp_path, *args):
    return main(["--config", write_config(tmp_path), "--env", str(tmp_path / "missing.env"), *args])


def test_dry_run_does_not_record_alerts(tmp_path, capsys):
    assert run(tmp_path, "daily", "--xml", str(FIXTURE), "--dry-run") == 0
    out = capsys.readouterr().out
    assert "Valor liquidativo" in out and "VZ cumple" in out
    store = Store(tmp_path / "data" / "divmon.sqlite")
    assert store.recent_alerts(__import__("datetime").datetime(2000, 1, 1)) == []
    assert store.radar_states() == {}


def test_daily_then_report_and_plan(tmp_path, capsys):
    assert run(tmp_path, "daily", "--xml", str(FIXTURE)) == 0
    store = Store(tmp_path / "data" / "divmon.sqlite")
    assert len(store.account_history()) == 1
    assert store.radar_states()["VZ"] == "cumple"
    assert (tmp_path / "data" / "flex" / "2026-09-25.xml").exists()

    capsys.readouterr()
    assert run(tmp_path, "daily", "--xml", str(FIXTURE)) == 0
    out = capsys.readouterr().out
    assert "Alertas nuevas enviadas: 0" in out
    assert "Todo en orden, sin avisos nuevos" in out and "ya enviados siguen vigentes" in out

    assert run(tmp_path, "report") == 0
    html = (tmp_path / "data" / "reports" / "informe-2026-09-25.html").read_text(encoding="utf-8")
    assert "Plan de amortización" in html and "data:image/png;base64" in html
    assert "no envía órdenes" in html

    assert run(tmp_path, "plan", "--aportacion", "600") == 0
    assert "600 €" in capsys.readouterr().out


def test_missing_flex_credentials_fails_cleanly(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("IB_FLEX_TOKEN", raising=False)
    assert run(tmp_path, "daily", "--dry-run") == 1
    assert "IB_FLEX_TOKEN" in capsys.readouterr().out


def test_config_rejects_unknown_keys(tmp_path):
    import pytest

    from divmon.config import ConfigError

    with pytest.raises(ConfigError, match="criteria"):
        base_config(tmp_path, criteria={"per_maximo": 10})


def test_import_history_only_adds_transactions(tmp_path, capsys):
    assert run(tmp_path, "daily", "--xml", str(FIXTURE)) == 0
    store = Store(tmp_path / "data" / "divmon.sqlite")
    positions = store.conn.execute("SELECT COUNT(*) FROM position_snapshots").fetchone()[0]
    assert run(tmp_path, "import-history", str(FIXTURE)) == 0
    assert len(store.cash_transactions()) > 30
    assert store.conn.execute("SELECT COUNT(*) FROM position_snapshots").fetchone()[0] == positions == 6
    assert run(tmp_path, "import-history", str(FIXTURE)) == 0
    assert "Total: 0" in capsys.readouterr().out


def test_email_channel_requires_credentials(tmp_path, monkeypatch):
    import pytest

    from divmon.alerts import make_notifier

    for var in ("SMTP_USER", "SMTP_PASSWORD", "EMAIL_TO"):
        monkeypatch.delenv(var, raising=False)
    cfg = base_config(tmp_path, alerts={"channel": "email"})
    with pytest.raises(RuntimeError, match="SMTP_USER"):
        make_notifier(cfg)
    monkeypatch.setenv("SMTP_USER", "yo@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "abcd efgh ijkl mnop")
    cfg = base_config(tmp_path, alerts={"channel": "email"})
    assert make_notifier(cfg).to == "yo@gmail.com"


def test_daily_digest_with_alerts(tmp_path, capsys):
    assert run(tmp_path, "daily", "--xml", str(FIXTURE)) == 0
    out = capsys.readouterr().out
    assert "avisos nuevos</b>" in out and "<b>Avisos nuevos</b>" in out
    assert "Próximo dividendo: MO 10/10" in out
    assert "Deuda a cero:" in out


def test_daily_without_summary_is_silent_when_nothing_new(tmp_path, capsys):
    cfg_path = write_config(tmp_path)
    data = yaml.safe_load(open(cfg_path))
    data["alerts"]["daily_summary"] = False
    open(cfg_path, "w").write(yaml.safe_dump(data))
    args = ["--config", cfg_path, "--env", str(tmp_path / "x.env"), "daily", "--xml", str(FIXTURE)]
    assert main(args) == 0
    capsys.readouterr()
    assert main(args) == 0
    assert "Cartera IBKR" not in capsys.readouterr().out.split("Alertas nuevas")[0].split("Próximos cobros")[-1]
