"""Carga de configuración: secretos en .env, parámetros en config.yaml."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


class ConfigError(ValueError):
    pass


@dataclass
class Criteria:
    per_max: float | None = None
    dividend_yield_min: float | None = None
    payout_max: float | None = None
    debt_ebitda_max: float | None = None

    def merged(self, override: dict[str, Any] | None) -> "Criteria":
        """Criterios con los ajustes de un valor concreto (null desactiva un criterio)."""
        if not override:
            return self
        values = {f.name: getattr(self, f.name) for f in fields(self)}
        for key, value in override.items():
            if key not in values:
                raise ConfigError(f"Criterio desconocido: {key}")
            values[key] = value
        return Criteria(**values)


@dataclass
class SymbolOverride:
    yahoo: str | None = None
    sector: str | None = None
    country: str | None = None
    maintenance_rate: float | None = None
    criteria: dict[str, Any] | None = None
    per: float | None = None
    dividend_yield: float | None = None
    payout: float | None = None
    debt_ebitda: float | None = None


@dataclass
class Candidate:
    symbol: str
    yahoo: str | None = None


@dataclass
class FlexConfig:
    enabled: bool = True
    token: str | None = None
    query_id: str | None = None


@dataclass
class GatewayConfig:
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 4002
    client_id: int = 17


@dataclass
class FundamentalsConfig:
    provider: str = "yahoo"
    max_age_days: int = 7


@dataclass
class MarginAlerts:
    loan_to_value_max: float | None = 0.30
    cushion_min: float | None = 0.25
    drop_to_call_min: float | None = 0.40


@dataclass
class MarginConfig:
    interest_rates: dict[str, float] = field(default_factory=dict)
    maintenance_rate_default: float = 0.25
    alerts: MarginAlerts = field(default_factory=MarginAlerts)


@dataclass
class ConcentrationConfig:
    position_max: float | None = 0.10
    country_max: float | None = 0.35
    sector_max: float | None = 0.30
    currency_max: float | None = 0.40
    exclude_base_currency: bool = True
    cooldown_hours: float = 168   # la concentración cambia despacio: como mucho un aviso semanal


@dataclass
class AmortizationConfig:
    monthly_contribution: float = 500.0
    dividends_to_debt: bool = True
    dividend_growth: float = 0.0


@dataclass
class RadarConfig:
    target_weight: float = 0.03
    candidates: list[Candidate] = field(default_factory=list)


@dataclass
class NewsConfig:
    enabled: bool = True
    max_per_symbol: int = 4
    max_age_days: int = 7
    min_weight: float = 0.01   # no buscar noticias de restos como NACON


@dataclass
class AlertsConfig:
    channel: str = "telegram"
    cooldown_hours: float = 72
    daily_summary: bool = True   # correo diario aunque no haya alertas, para saber que todo funciona
    telegram_token: str | None = None
    telegram_chat_id: str | None = None
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_user: str | None = None
    smtp_password: str | None = None
    email_to: str | None = None


@dataclass
class Config:
    base_currency: str = "EUR"
    data_dir: Path = Path("data")
    flex: FlexConfig = field(default_factory=FlexConfig)
    ib_gateway: GatewayConfig = field(default_factory=GatewayConfig)
    fundamentals: FundamentalsConfig = field(default_factory=FundamentalsConfig)
    criteria: Criteria = field(default_factory=Criteria)
    margin: MarginConfig = field(default_factory=MarginConfig)
    concentration: ConcentrationConfig = field(default_factory=ConcentrationConfig)
    amortization: AmortizationConfig = field(default_factory=AmortizationConfig)
    radar: RadarConfig = field(default_factory=RadarConfig)
    symbols: dict[str, SymbolOverride] = field(default_factory=dict)
    news: NewsConfig = field(default_factory=NewsConfig)
    alerts: AlertsConfig = field(default_factory=AlertsConfig)

    @property
    def db_path(self) -> Path:
        return self.data_dir / "divmon.sqlite"

    @property
    def flex_dir(self) -> Path:
        return self.data_dir / "flex"

    @property
    def reports_dir(self) -> Path:
        return self.data_dir / "reports"

    def override(self, symbol: str) -> SymbolOverride:
        return self.symbols.get(symbol, SymbolOverride())

    def criteria_for(self, symbol: str) -> Criteria:
        return self.criteria.merged(self.override(symbol).criteria)


def _build(cls, data: dict[str, Any] | None, section: str):
    data = dict(data or {})
    known = {f.name for f in fields(cls)}
    unknown = set(data) - known
    if unknown:
        raise ConfigError(f"Claves desconocidas en '{section}': {', '.join(sorted(unknown))}")
    return cls(**data)


def load_config(config_path: str | Path = "config.yaml", env_path: str | Path | None = ".env") -> Config:
    if env_path and Path(env_path).exists():
        load_dotenv(env_path)
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(f"No existe {path}. Copia config.example.yaml a config.yaml y ajústalo.")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return config_from_dict(raw, base_dir=path.parent)


def config_from_dict(raw: dict[str, Any], base_dir: Path = Path(".")) -> Config:
    raw = dict(raw)
    margin_raw = dict(raw.pop("margin", {}) or {})
    margin = MarginConfig(
        interest_rates={k.upper(): float(v) for k, v in (margin_raw.pop("interest_rates", {}) or {}).items()},
        maintenance_rate_default=float(margin_raw.pop("maintenance_rate_default", 0.25)),
        alerts=_build(MarginAlerts, margin_raw.pop("alerts", None), "margin.alerts"),
    )
    if margin_raw:
        raise ConfigError(f"Claves desconocidas en 'margin': {', '.join(sorted(margin_raw))}")

    radar_raw = dict(raw.pop("radar", {}) or {})
    candidates = [
        _build(Candidate, c if isinstance(c, dict) else {"symbol": c}, "radar.candidates")
        for c in radar_raw.pop("candidates", []) or []
    ]
    radar = RadarConfig(candidates=candidates, **radar_raw)

    symbols = {
        str(sym): _build(SymbolOverride, ov, f"symbols.{sym}")
        for sym, ov in (raw.pop("symbols", {}) or {}).items()
    }

    flex = _build(FlexConfig, raw.pop("flex", None), "flex")
    flex.token = flex.token or os.getenv("IB_FLEX_TOKEN") or None
    flex.query_id = flex.query_id or os.getenv("IB_FLEX_QUERY_ID") or None

    alerts = _build(AlertsConfig, raw.pop("alerts", None), "alerts")
    alerts.telegram_token = alerts.telegram_token or os.getenv("TELEGRAM_BOT_TOKEN") or None
    alerts.telegram_chat_id = alerts.telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID") or None
    alerts.smtp_user = alerts.smtp_user or os.getenv("SMTP_USER") or None
    alerts.smtp_password = alerts.smtp_password or os.getenv("SMTP_PASSWORD") or None
    alerts.email_to = alerts.email_to or os.getenv("EMAIL_TO") or alerts.smtp_user

    data_dir = Path(raw.pop("data_dir", "data"))
    if not data_dir.is_absolute():
        data_dir = base_dir / data_dir

    cfg = Config(
        base_currency=str(raw.pop("base_currency", "EUR")).upper(),
        data_dir=data_dir,
        flex=flex,
        ib_gateway=_build(GatewayConfig, raw.pop("ib_gateway", None), "ib_gateway"),
        fundamentals=_build(FundamentalsConfig, raw.pop("fundamentals", None), "fundamentals"),
        criteria=_build(Criteria, raw.pop("criteria", None), "criteria"),
        margin=margin,
        concentration=_build(ConcentrationConfig, raw.pop("concentration", None), "concentration"),
        amortization=_build(AmortizationConfig, raw.pop("amortization", None), "amortization"),
        radar=radar,
        symbols=symbols,
        news=_build(NewsConfig, raw.pop("news", None), "news"),
        alerts=alerts,
    )
    if raw:
        raise ConfigError(f"Secciones desconocidas en config.yaml: {', '.join(sorted(raw))}")
    if cfg.alerts.channel not in {"telegram", "email", "console"}:
        raise ConfigError("alerts.channel debe ser 'telegram', 'email' o 'console'")
    if cfg.fundamentals.provider not in {"yahoo", "none"}:
        raise ConfigError("fundamentals.provider debe ser 'yahoo' o 'none'")
    return cfg
