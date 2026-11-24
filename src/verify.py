"""Verifikasi hasil ingestion pada Azure Blob Storage."""

from __future__ import annotations

import datetime as dt
import os
import sys

from .config import CONTAINER, TICKERS
from .storage import BlobSink


def main() -> int:
    as_of = os.getenv("AS_OF") or dt.date.today().isoformat()
    sink = BlobSink()

    blobs = [name for name in sink.list("bronze/prices/") if name.endswith(".parquet")]
    today = [name for name in blobs if f"ingest_date={as_of}" in name]

    print(f"container        : {CONTAINER}")
    print(f"tanggal acuan    : {as_of}")
    print(f"total parquet    : {len(blobs)}")
    print(f"parquet hari ini : {len(today)} / {len(TICKERS)}")
    for name in today:
        print("  -", name)

    if len(today) < len(TICKERS):
        print("[gagal] jumlah ticker hari ini belum lengkap", file=sys.stderr)
        return 1
    print("[ok] seluruh instrumen tersedia di Azure Blob Storage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
