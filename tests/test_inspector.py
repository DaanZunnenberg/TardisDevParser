import responses

from tardis_reader.inspector import METADATA_BASE_URL, TardisInspector


@responses.activate
def test_check_credentials_valid_key_uses_metadata_probe_target():
    responses.add(
        responses.GET,
        f"{METADATA_BASE_URL}/exchanges/bitmex",
        json={
            "id": "bitmex",
            "datasets": {
                "symbols": [{"id": "XBTUSD", "availableSince": "2018-05-04T00:00:00.000Z"}]
            },
        },
        status=200,
    )
    responses.add(
        responses.HEAD,
        "https://datasets.tardis.dev/v1/bitmex/trades/2018/05/04/XBTUSD.csv.gz",
        status=200,
    )

    inspector = TardisInspector(api_key="good-key")
    result = inspector.check_credentials()

    assert result.valid is True
    assert result.status_code == 200
    assert "2018/05/04" in result.probe_url


@responses.activate
def test_check_credentials_invalid_key_returns_false():
    responses.add(
        responses.GET,
        f"{METADATA_BASE_URL}/exchanges/bitmex",
        json={"id": "bitmex", "datasets": {"symbols": []}},
        status=200,
    )
    responses.add(
        responses.HEAD,
        "https://datasets.tardis.dev/v1/bitmex/trades/2019/01/02/XBTUSD.csv.gz",
        status=401,
    )

    inspector = TardisInspector(api_key="bad-key")
    result = inspector.check_credentials()

    assert result.valid is False
    assert result.status_code == 401


@responses.activate
def test_check_credentials_falls_back_when_metadata_lookup_fails():
    responses.add(
        responses.GET,
        f"{METADATA_BASE_URL}/exchanges/bitmex",
        json={"error": "boom"},
        status=500,
    )
    responses.add(
        responses.HEAD,
        "https://datasets.tardis.dev/v1/bitmex/trades/2019/01/02/XBTUSD.csv.gz",
        status=200,
    )

    inspector = TardisInspector(api_key="good-key")
    result = inspector.check_credentials()

    assert result.valid is True


@responses.activate
def test_list_exchanges_returns_raw_json():
    responses.add(
        responses.GET,
        f"{METADATA_BASE_URL}/exchanges",
        json=[{"id": "binance", "name": "Binance"}],
        status=200,
    )

    inspector = TardisInspector()
    exchanges = inspector.list_exchanges()

    assert exchanges == [{"id": "binance", "name": "Binance"}]


@responses.activate
def test_describe_exchange_returns_raw_json():
    responses.add(
        responses.GET,
        f"{METADATA_BASE_URL}/exchanges/deribit",
        json={"id": "deribit", "datasets": {"dataTypes": ["trades"], "symbols": []}},
        status=200,
    )

    inspector = TardisInspector()
    details = inspector.describe_exchange("deribit")

    assert details["datasets"]["dataTypes"] == ["trades"]
