"""Konfigurasi pipeline: daftar instrumen, lokasi penyimpanan, helper nama blob."""

from __future__ import annotations

import os
import re
from pathlib import Path

# Delapan instrumen pada Tabel 3.5 laporan. ^JKSE adalah objek prediksi.
TICKERS: list[str] = [
    "^JKSE",
    "CL=F",
    "GC=F",
    "IDR=X",
    "^HSI",
    "^N225",
    "^DJI",
    "EEM",
]
TARGET = "^JKSE"
START = "2018-01-01"

ACCOUNT = os.getenv("AZURE_STORAGE_ACCOUNT", "").strip()
CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER", "ihsg-lake").strip()
DATA_DIR = Path(os.getenv("LOCAL_DATA_DIR", "data"))


def safe(ticker: str) -> str:
    """Ubah simbol ticker menjadi nama yang aman untuk nama blob.

    ^JKSE -> JKSE, CL=F -> CL_F, IDR=X -> IDR_X
    """
    return re.sub(r"[^A-Za-z0-9]+", "_", ticker).strip("_")
