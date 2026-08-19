# Tardis.dev Data Fetcher

A small, focused client for downloading historical cryptocurrency market data
from [Tardis-dev](https://tardis.dev). It handles authentication, configuring
what data to pull (exchange, data types, symbols, date range), and writing the
downloaded files to disk.

This project is scoped to **fetching only**. It does not parse, clean,
store (beyond raw files on disk), or visualize data — that's for later stages
of the pipeline (see `CLAUDE.md`).

## Project structure

```
TardisDevParser/
├── CLAUDE.md                    # High-level project brief/roadmap
├── README.md                    # This file
├── pyproject.toml               # Package metadata, deps, console scripts
├── .env.example                 # Template for the TARDIS_API_KEY env var
├── .gitignore
│
├── config/
│   └── example.yaml             # Sample fetch options
│
├── src/tardis_reader/           # The installable package
│   ├── __init__.py              # Public exports
│   ├── config.py                # FetchOptions: loads/validates/merges options
│   ├── client.py                # TardisClient: downloads data from the Datasets API
│   ├── inspector.py             # TardisInspector: checks API key, lists available data
│   ├── exceptions.py            # TardisConfigError / TardisAuthError / TardisAPIError
│   ├── cli.py                   # `tardis-fetch` entrypoint
│   └── inspect_cli.py           # `tardis-inspect` entrypoint
│
└── tests/
    ├── test_config.py           # FetchOptions parsing & validation
    ├── test_client.py           # Download / skip-existing / error-handling behavior
    └── test_inspector.py        # Credential check & metadata discovery
```

## How the pieces fit together

- **`config.py`** — `FetchOptions` is a validated dataclass describing one
  fetch job: exchange, data types, symbols, date range, output directory,
  format, and API key. `FetchOptions.from_sources()` merges three layers, in
  priority order: **CLI flags > config file (YAML/JSON) > `TARDIS_API_KEY`
  env var**. This is what lets you keep a reusable `config/example.yaml` and
  override just the pieces you want per run.

- **`client.py`** — `TardisClient` builds Tardis.dev Datasets API URLs from a
  `FetchOptions`, authenticates with a bearer token, retries transient
  failures (429/5xx) with backoff, streams each file to disk, and skips files
  that already exist unless `--overwrite` is set. It raises
  `TardisAuthError` on 401/403 and `TardisAPIError` on other failures.

- **`inspector.py`** — `TardisInspector` is a read-only companion to the
  client: `check_credentials()` verifies an API key without downloading any
  real data (it does a `HEAD` request against a known-available dataset), and
  `list_exchanges()` / `describe_exchange()` query Tardis.dev's public
  metadata API to show which exchanges, data types, symbols, and date ranges
  are available — useful for figuring out valid `FetchOptions` values before
  running a real fetch.

- **`exceptions.py`** — three exception types (`TardisConfigError`,
  `TardisAuthError`, `TardisAPIError`) used across the package so callers can
  distinguish "your config is wrong" from "your key is wrong" from "the API
  had a problem."

- **`cli.py`** / **`inspect_cli.py`** — thin argparse wrappers exposing the
  above as two console scripts, `tardis-fetch` and `tardis-inspect`.

## Installation

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Set your API key once, via environment variable:

```bash
cp .env.example .env   # then edit .env with your real key
export TARDIS_API_KEY=your-tardis-dev-api-key-here
```

## Usage

### Check your API key and browse available data

```bash
# Verify the API key works (uses TARDIS_API_KEY, or pass --api-key)
tardis-inspect check-key

# List every exchange Tardis.dev has data for
tardis-inspect exchanges

# See data types, symbols, and date ranges available for one exchange
tardis-inspect describe binance
```

### Fetch data

Using a config file:

```bash
tardis-fetch --config config/example.yaml
```

Or entirely via flags:

```bash
tardis-fetch \
  --exchange binance \
  --data-types trades,book_snapshot_25 \
  --symbols BTCUSDT,ETHUSDT \
  --from-date 2024-01-01 \
  --to-date 2024-01-07 \
  --output-dir ./data
```

CLI flags always override the config file, which overrides the
`TARDIS_API_KEY` environment variable.

Downloaded files land under `<output_dir>/<exchange>/<data_type>/<symbol>/<date>.csv.gz`.

## Running tests

```bash
pytest
```
