from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime

import requests

from .exceptions import TardisAPIError

logger = logging.getLogger(__name__)

METADATA_BASE_URL = "https://api.tardis.dev/v1"
DATASETS_BASE_URL = "https://datasets.tardis.dev/v1"

# Used as a last resort to probe an API key when the metadata API can't tell us
# a guaranteed-available symbol/date for the exchange we're checking.
FALLBACK_PROBE = {"exchange": "bitmex", "data_type": "trades", "symbol": "XBTUSD"}
FALLBACK_PROBE_DATE = date(2019, 1, 2)


@dataclass
class CredentialCheckResult:
    valid: bool
    status_code: int | None
    message: str
    probe_url: str


class TardisInspector:
    """Read-only helper for checking API key validity and browsing what data
    Tardis.dev has on offer, without downloading any actual datasets.
    """

    def __init__(self, api_key: str = "", session: requests.Session | None = None):
        self.api_key = api_key
        self.session = session or requests.Session()

    # -- credentials ----------------------------------------------------

    def check_credentials(self) -> CredentialCheckResult:
        """Verify the API key against the Datasets API.

        Picks a symbol/date that the exchange metadata says has been
        available since day one, then makes a HEAD request for it so no
        data is actually downloaded.
        """
        exchange = FALLBACK_PROBE["exchange"]
        data_type = FALLBACK_PROBE["data_type"]
        symbol = FALLBACK_PROBE["symbol"]
        probe_date = FALLBACK_PROBE_DATE

        try:
            details = self.describe_exchange(exchange)
            datasets = details.get("datasets", {})
            symbols = datasets.get("symbols", [])
            if symbols:
                first = symbols[0]
                symbol = first.get("id", symbol)
                since = first.get("availableSince")
                if since:
                    probe_date = _parse_iso_date(since)
        except (TardisAPIError, requests.RequestException):
            logger.debug("metadata lookup failed, using fallback probe target")

        url = (
            f"{DATASETS_BASE_URL}/{exchange}/{data_type}"
            f"/{probe_date:%Y}/{probe_date:%m}/{probe_date:%d}/{symbol}.csv.gz"
        )
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

        response = self.session.head(url, headers=headers, timeout=30, allow_redirects=True)

        if response.status_code == 200:
            return CredentialCheckResult(True, response.status_code, "API key is valid.", url)
        if response.status_code in (401, 403):
            return CredentialCheckResult(
                False, response.status_code, "API key was rejected by Tardis.dev.", url
            )
        return CredentialCheckResult(
            False,
            response.status_code,
            f"Unexpected response ({response.status_code}); could not confirm key validity.",
            url,
        )

    # -- discovery --------------------------------------------------------

    def list_exchanges(self) -> list[dict]:
        """Return the raw exchange metadata list (public, no API key required)."""
        return self._get_json(f"{METADATA_BASE_URL}/exchanges")

    def describe_exchange(self, exchange: str) -> dict:
        """Return metadata for one exchange: available data types, symbols,
        and the date range each symbol's data is available for.
        """
        return self._get_json(f"{METADATA_BASE_URL}/exchanges/{exchange}")

    def _get_json(self, url: str) -> dict | list:
        response = self.session.get(url, timeout=30)
        if not response.ok:
            raise TardisAPIError(
                f"unexpected response {response.status_code} for {url}: {response.text[:500]}",
                status_code=response.status_code,
                url=url,
            )
        return response.json()


def _parse_iso_date(value: str) -> date:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return FALLBACK_PROBE_DATE
