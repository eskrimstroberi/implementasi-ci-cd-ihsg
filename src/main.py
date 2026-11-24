"""Orkestrasi pipeline: unduh 8 instrumen, simpan Parquet, tulis manifest."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

import pandas as pd
import yfinance as yf

from .config import ACCOUNT, START, TICKERS, safe
from .ingest import fetch
from .storage import BlobSink, LocalSink


def fingerprint(df: pd.DataFrame) -> str:
    """SHA-256 isi tabel, dicatat pada manifest untuk penelusuran asal data."""
    return hashlib.sha256(pd.util.hash_pandas_object(df, index=False).values.tobytes()).hexdigest()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m src.main")
    parser.add_argument("--local", action="store_true", help="simpan ke ./data, tanpa Azure")
    parser.add_argument("--start", default=START, help=f"tanggal awal unduh (default {START})")
    parser.add_argument("--as-of", default=None, help="tanggal acuan YYYY-MM-DD")
    parser.add_argument("--tickers", nargs="*", default=None, help="batasi ke ticker tertentu")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    as_of = args.as_of or dt.date.today().isoformat()
    tickers = args.tickers or TICKERS
    sink = LocalSink() if args.local else BlobSink()

    summary: dict[str, dict] = {}
    total_rows = 0

    for ticker in tickers:
        df = fetch(ticker, args.start)
        path = f"bronze/prices/ticker={safe(ticker)}/ingest_date={as_of}/prices.parquet"
        sink.write_parquet(path, df)

        rows = len(df)
        total_rows += rows
        summary[ticker] = {
            "rows": rows,
            "start": df["date"].min().date().isoformat(),
            "end": df["date"].max().date().isoformat(),
            "sha256": fingerprint(df),
            "path": path,
        }
        print(
            f"[ok] {ticker:<6} {rows:>5} baris  "
            f"{summary[ticker]['start']}..{summary[ticker]['end']}",
            flush=True,
        )

    manifest = {
        "as_of": as_of,
        "run_at_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "source": "yfinance",
        "yfinance_version": yf.__version__,
        "start": args.start,
        "total_rows": total_rows,
        "destination": "local" if args.local else ACCOUNT,
        "tickers": summary,
    }

    manifest_path = f"bronze/_manifest/ingest_date={as_of}/manifest.json"
    sink.write_json(manifest_path, manifest)

    # Salinan lokal selalu dibuat agar bisa diunggah sebagai artifact di Actions.
    local_copy = Path("data") / manifest_path
    local_copy.parent.mkdir(parents=True, exist_ok=True)
    local_copy.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[ok] total {total_rows} baris dari {len(tickers)} instrumen")
    print(f"[ok] manifest -> {manifest_path}")
    print(json.dumps({k: manifest[k] for k in ("as_of", "total_rows", "run_at_utc")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
