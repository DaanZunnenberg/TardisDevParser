from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from .exceptions import TardisConfigError

API_KEY_ENV_VAR = "TARDIS_API_KEY"


@dataclass
class FetchOptions:
    """Describes one download job: what data to pull from Tardis.dev and where to put it.

    Precedence when built via `from_sources`: CLI args > config file > env vars > defaults.
    """

    exchange: str
    data_types: list[str]
    symbols: list[str]
    from_date: date
    to_date: date
    output_dir: Path = Path("./data")
    api_key: str = ""
    format: str = "csv"
    overwrite: bool = False

    def __post_init__(self) -> None:
        if not self.exchange:
            raise TardisConfigError("exchange is required")
        if not self.data_types:
            raise TardisConfigError("at least one data_type is required")
        if not self.symbols:
            raise TardisConfigError("at least one symbol is required")
        if self.from_date > self.to_date:
            raise TardisConfigError(
                f"from_date ({self.from_date}) must not be after to_date ({self.to_date})"
            )
        if not self.api_key:
            raise TardisConfigError(
                f"api_key is required (set it in the config file, pass --api-key, "
                f"or set the {API_KEY_ENV_VAR} environment variable)"
            )
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)

    def date_range(self) -> list[date]:
        days = (self.to_date - self.from_date).days
        return [self.from_date + timedelta(days=i) for i in range(days + 1)]

    @classmethod
    def from_sources(cls, config_path: str | Path | None, overrides: dict) -> "FetchOptions":
        """Merge a YAML/JSON config file, environment variables, and CLI overrides.

        `overrides` should only contain keys the user explicitly passed on the CLI
        (i.e. leave keys out entirely rather than passing them as None) so config
        file values aren't clobbered by unset argparse defaults.
        """
        raw: dict = {}
        if config_path:
            raw = _load_file(Path(config_path))

        raw.update({k: v for k, v in overrides.items() if v is not None})

        if not raw.get("api_key"):
            env_key = os.environ.get(API_KEY_ENV_VAR)
            if env_key:
                raw["api_key"] = env_key

        try:
            from_date = _parse_date(raw["from_date"])
            to_date = _parse_date(raw["to_date"])
        except KeyError as exc:
            raise TardisConfigError(f"missing required option: {exc}") from exc

        data_types = raw.get("data_types")
        if isinstance(data_types, str):
            data_types = [d.strip() for d in data_types.split(",") if d.strip()]

        symbols = raw.get("symbols")
        if isinstance(symbols, str):
            symbols = [s.strip() for s in symbols.split(",") if s.strip()]

        return cls(
            exchange=raw.get("exchange", ""),
            data_types=data_types or [],
            symbols=symbols or [],
            from_date=from_date,
            to_date=to_date,
            output_dir=raw.get("output_dir", "./data"),
            api_key=raw.get("api_key", ""),
            format=raw.get("format", "csv"),
            overwrite=bool(raw.get("overwrite", False)),
        )


def _load_file(path: Path) -> dict:
    if not path.exists():
        raise TardisConfigError(f"config file not found: {path}")
    text = path.read_text()
    if path.suffix in (".yaml", ".yml"):
        data = yaml.safe_load(text)
    elif path.suffix == ".json":
        import json

        data = json.loads(text)
    else:
        raise TardisConfigError(f"unsupported config file extension: {path.suffix}")
    return data or {}


def _parse_date(value) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError as exc:
        raise TardisConfigError(f"invalid date '{value}', expected YYYY-MM-DD") from exc
