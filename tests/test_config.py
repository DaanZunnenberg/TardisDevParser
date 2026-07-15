import pytest

from tardis_reader.config import FetchOptions
from tardis_reader.exceptions import TardisConfigError


def base_overrides(**extra):
    overrides = {
        "exchange": "binance",
        "data_types": "trades,book_snapshot_25",
        "symbols": "BTCUSDT,ETHUSDT",
        "from_date": "2024-01-01",
        "to_date": "2024-01-03",
        "api_key": "test-key",
    }
    overrides.update(extra)
    return overrides


def test_from_sources_parses_csv_lists_and_dates():
    options = FetchOptions.from_sources(None, base_overrides())
    assert options.data_types == ["trades", "book_snapshot_25"]
    assert options.symbols == ["BTCUSDT", "ETHUSDT"]
    assert len(options.date_range()) == 3


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("TARDIS_API_KEY", raising=False)
    with pytest.raises(TardisConfigError):
        FetchOptions.from_sources(None, base_overrides(api_key=None))


def test_from_date_after_to_date_raises():
    with pytest.raises(TardisConfigError):
        FetchOptions.from_sources(
            None, base_overrides(from_date="2024-01-10", to_date="2024-01-01")
        )


def test_env_var_used_when_api_key_absent(monkeypatch):
    monkeypatch.setenv("TARDIS_API_KEY", "env-key")
    options = FetchOptions.from_sources(None, base_overrides(api_key=None))
    assert options.api_key == "env-key"
