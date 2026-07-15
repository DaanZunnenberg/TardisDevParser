from datetime import date

import pytest
import responses

from tardis_reader.client import TardisClient
from tardis_reader.config import FetchOptions
from tardis_reader.exceptions import TardisAPIError, TardisAuthError


def make_options(tmp_path, **extra):
    defaults = dict(
        exchange="binance",
        data_types=["trades"],
        symbols=["BTCUSDT"],
        from_date=date(2024, 1, 1),
        to_date=date(2024, 1, 1),
        output_dir=tmp_path,
        api_key="test-key",
    )
    defaults.update(extra)
    return FetchOptions(**defaults)


@responses.activate
def test_fetch_one_writes_file(tmp_path):
    options = make_options(tmp_path)
    client = TardisClient(options)
    url = client.build_url("trades", "BTCUSDT", date(2024, 1, 1))
    responses.add(responses.GET, url, body=b"gzip-bytes", status=200)

    dest = client.fetch_one("trades", "BTCUSDT", date(2024, 1, 1))

    assert dest.exists()
    assert dest.read_bytes() == b"gzip-bytes"


@responses.activate
def test_fetch_one_skips_existing_file(tmp_path):
    options = make_options(tmp_path, overwrite=False)
    client = TardisClient(options)
    dest = client.local_path("trades", "BTCUSDT", date(2024, 1, 1))
    dest.parent.mkdir(parents=True)
    dest.write_bytes(b"already-here")

    result = client.fetch_one("trades", "BTCUSDT", date(2024, 1, 1))

    assert result == dest
    assert dest.read_bytes() == b"already-here"
    assert len(responses.calls) == 0


@responses.activate
def test_fetch_one_raises_auth_error_on_401(tmp_path):
    options = make_options(tmp_path)
    client = TardisClient(options)
    url = client.build_url("trades", "BTCUSDT", date(2024, 1, 1))
    responses.add(responses.GET, url, status=401)

    with pytest.raises(TardisAuthError):
        client.fetch_one("trades", "BTCUSDT", date(2024, 1, 1))


@responses.activate
def test_fetch_one_raises_api_error_on_404(tmp_path):
    options = make_options(tmp_path)
    client = TardisClient(options)
    url = client.build_url("trades", "BTCUSDT", date(2024, 1, 1))
    responses.add(responses.GET, url, status=404)

    with pytest.raises(TardisAPIError):
        client.fetch_one("trades", "BTCUSDT", date(2024, 1, 1))
