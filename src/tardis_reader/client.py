from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import FetchOptions
from .exceptions import TardisAPIError, TardisAuthError

logger = logging.getLogger(__name__)

DATASETS_BASE_URL = "https://datasets.tardis.dev/v1"


class TardisClient:
    """Thin wrapper around the Tardis.dev Datasets HTTP API.

    Handles authentication, retries on transient failures, and writing
    the downloaded (already-gzipped) files to disk. Does not parse or
    transform the data it downloads.
    """

    def __init__(self, options: FetchOptions, session: requests.Session | None = None):
        self.options = options
        self.session = session or self._build_session()

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=5,
            backoff_factor=1.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.headers["Authorization"] = f"Bearer {self.options.api_key}"
        return session

    def build_url(self, data_type: str, symbol: str, day: date) -> str:
        return (
            f"{DATASETS_BASE_URL}/{self.options.exchange}/{data_type}"
            f"/{day:%Y}/{day:%m}/{day:%d}/{symbol}.{self.options.format}.gz"
        )

    def local_path(self, data_type: str, symbol: str, day: date) -> Path:
        return (
            self.options.output_dir
            / self.options.exchange
            / data_type
            / symbol
            / f"{day:%Y-%m-%d}.{self.options.format}.gz"
        )

    def fetch_all(self) -> list[Path]:
        """Download every (data_type x symbol x day) combination in the options.

        Returns the list of local file paths written (or already present, if
        `overwrite` is False and the file existed).
        """
        written: list[Path] = []
        for data_type in self.options.data_types:
            for symbol in self.options.symbols:
                for day in self.options.date_range():
                    written.append(self.fetch_one(data_type, symbol, day))
        return written

    def fetch_one(self, data_type: str, symbol: str, day: date) -> Path:
        dest = self.local_path(data_type, symbol, day)

        if dest.exists() and not self.options.overwrite:
            logger.info("skip (already exists): %s", dest)
            return dest

        url = self.build_url(data_type, symbol, day)
        logger.info("fetching %s -> %s", url, dest)

        response = self.session.get(url, stream=True, timeout=60)
        self._raise_for_status(response, url)

        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = dest.with_suffix(dest.suffix + ".part")
        with open(tmp_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)
        tmp_path.replace(dest)
        return dest

    @staticmethod
    def _raise_for_status(response: requests.Response, url: str) -> None:
        if response.status_code == 401 or response.status_code == 403:
            raise TardisAuthError(
                f"Tardis.dev rejected the API key (status {response.status_code}) for {url}"
            )
        if response.status_code == 404:
            raise TardisAPIError(
                f"no data found at {url} (check exchange/data type/symbol/date)",
                status_code=404,
                url=url,
            )
        if not response.ok:
            raise TardisAPIError(
                f"unexpected response {response.status_code} for {url}: {response.text[:500]}",
                status_code=response.status_code,
                url=url,
            )
