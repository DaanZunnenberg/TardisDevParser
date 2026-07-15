from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from .config import API_KEY_ENV_VAR
from .exceptions import TardisAPIError
from .inspector import TardisInspector


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tardis-inspect",
        description="Check a Tardis.dev API key and browse available data.",
    )
    parser.add_argument("--api-key", help=f"defaults to the {API_KEY_ENV_VAR} env var")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable debug logging")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("check-key", help="verify the API key against Tardis.dev")

    exchanges_parser = subparsers.add_parser(
        "exchanges", help="list all exchanges Tardis.dev has data for"
    )
    exchanges_parser.add_argument(
        "--json", action="store_true", help="print raw JSON instead of a summary table"
    )

    describe_parser = subparsers.add_parser(
        "describe", help="show data types, symbols, and date ranges for one exchange"
    )
    describe_parser.add_argument("exchange", help="e.g. binance, deribit, bitmex")
    describe_parser.add_argument(
        "--json", action="store_true", help="print raw JSON instead of a summary"
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    api_key = args.api_key or os.environ.get(API_KEY_ENV_VAR, "")
    inspector = TardisInspector(api_key=api_key)

    try:
        if args.command == "check-key":
            return _check_key(inspector)
        if args.command == "exchanges":
            return _list_exchanges(inspector, as_json=args.json)
        if args.command == "describe":
            return _describe_exchange(inspector, args.exchange, as_json=args.json)
    except TardisAPIError as exc:
        print(f"API error: {exc}", file=sys.stderr)
        return 4

    return 1


def _check_key(inspector: TardisInspector) -> int:
    if not inspector.api_key:
        print(
            f"No API key supplied (use --api-key or set {API_KEY_ENV_VAR}).",
            file=sys.stderr,
        )
        return 2

    result = inspector.check_credentials()
    print(result.message)
    print(f"  probed: {result.probe_url}")
    print(f"  status: {result.status_code}")
    return 0 if result.valid else 1


def _list_exchanges(inspector: TardisInspector, as_json: bool) -> int:
    exchanges = inspector.list_exchanges()

    if as_json:
        print(json.dumps(exchanges, indent=2))
        return 0

    for entry in exchanges:
        exchange_id = entry.get("id", "?")
        name = entry.get("name", exchange_id)
        since = entry.get("availableSince", "?")
        print(f"{exchange_id:<15} {name:<25} available since {since}")
    return 0


def _describe_exchange(inspector: TardisInspector, exchange: str, as_json: bool) -> int:
    details = inspector.describe_exchange(exchange)

    if as_json:
        print(json.dumps(details, indent=2))
        return 0

    print(f"{details.get('name', exchange)} ({details.get('id', exchange)})")

    data_types = details.get("datasets", {}).get("dataTypes")
    if data_types:
        print("\nData types:")
        for dt in data_types:
            print(f"  - {dt}")

    symbols = details.get("datasets", {}).get("symbols", [])
    if symbols:
        print(f"\nSymbols ({len(symbols)}):")
        for sym in symbols[:50]:
            sym_id = sym.get("id", "?")
            since = sym.get("availableSince", "?")
            until = sym.get("availableTo", "present")
            print(f"  - {sym_id:<15} {since} -> {until}")
        if len(symbols) > 50:
            print(f"  ... and {len(symbols) - 50} more (use --json to see all)")

    if not data_types and not symbols:
        print("\n(no structured dataset metadata found; showing raw response)")
        print(json.dumps(details, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
