from __future__ import annotations

import argparse
import logging
import sys

from .client import TardisClient
from .config import FetchOptions
from .exceptions import TardisAPIError, TardisAuthError, TardisConfigError


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tardis-fetch",
        description="Download historical market data from Tardis.dev.",
    )
    parser.add_argument("-c", "--config", help="path to a YAML/JSON config file")
    parser.add_argument("--exchange", help="e.g. binance, deribit, bitmex")
    parser.add_argument(
        "--data-types", help="comma-separated list, e.g. trades,book_snapshot_25"
    )
    parser.add_argument("--symbols", help="comma-separated list, e.g. BTCUSDT,ETHUSDT")
    parser.add_argument("--from-date", help="YYYY-MM-DD, inclusive")
    parser.add_argument("--to-date", help="YYYY-MM-DD, inclusive")
    parser.add_argument("--output-dir", help="directory to write downloaded files to")
    parser.add_argument("--api-key", help="Tardis.dev API key (overrides env/config)")
    parser.add_argument("--format", help="dataset format, default csv")
    parser.add_argument(
        "--overwrite", action="store_true", default=None, help="re-download existing files"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="enable debug logging")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    overrides = {
        "exchange": args.exchange,
        "data_types": args.data_types,
        "symbols": args.symbols,
        "from_date": args.from_date,
        "to_date": args.to_date,
        "output_dir": args.output_dir,
        "api_key": args.api_key,
        "format": args.format,
        "overwrite": args.overwrite,
    }

    try:
        options = FetchOptions.from_sources(args.config, overrides)
        client = TardisClient(options)
        written = client.fetch_all()
    except TardisConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except TardisAuthError as exc:
        print(f"Authentication error: {exc}", file=sys.stderr)
        return 3
    except TardisAPIError as exc:
        print(f"API error: {exc}", file=sys.stderr)
        return 4

    print(f"Done. {len(written)} file(s) available under {options.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
