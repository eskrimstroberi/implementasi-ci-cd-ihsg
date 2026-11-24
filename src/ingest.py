"""Pengambilan data harian dari Yahoo Finance melalui pustaka yfinance."""

from __future__ import annotations

import time

import pandas as pd
import yfinance as yf

COLUMNS = ["date", "ticker", "open", "high", "low", "close", "adj_close", "volume"]


class IngestError(RuntimeError):
    """Kegagalan yang membuat pipeline harus berhenti."""


def fetch(ticker: str, start: str, retries: int = 3, pause: float = 2.0) -> pd.DataFrame:
    """Unduh OHLCV harian satu ticker, dengan percobaan ulang terkendali.

    auto_adjust=False dipakai agar harga mentah dan harga disesuaikan tersimpan
    terpisah, sesuai keputusan desain pada Bab III laporan.
    """
    last_error: Exception | None = None

    for attempt in range(retries):
        try:
            raw = yf.Ticker(ticker).history(
                start=start, auto_adjust=False, actions=False
            )
            if raw.empty:
                raise IngestError(f"{ticker}: tidak ada data pada rentang {start}")

            df = raw.reset_index()
            df.columns = [str(col).lower().replace(" ", "_") for col in df.columns]
            df["date"] = (
                pd.to_datetime(df["date"], utc=True).dt.tz_localize(None).dt.normalize()
            )
            df["ticker"] = ticker

            missing = [col for col in COLUMNS if col not in df.columns]
            if missing:
                raise IngestError(f"{ticker}: kolom tidak lengkap, hilang {missing}")

            df = df[COLUMNS].sort_values("date").drop_duplicates("date", keep="last")
            return df.reset_index(drop=True)
        except Exception as exc:  # noqa: BLE001 - semua kegagalan diulang sekali
            last_error = exc
            if attempt < retries - 1:
                time.sleep(pause * (attempt + 1))

    raise IngestError(f"gagal mengunduh {ticker} setelah {retries} percobaan: {last_error}")
