import pandas as pd
import pytest

from src.config import TICKERS, safe
from src.ingest import COLUMNS
from src.storage import LocalSink


def test_delapan_instrumen_sesuai_laporan():
    assert len(TICKERS) == 8
    assert TICKERS[0] == "^JKSE"


def test_nama_blob_aman_untuk_simbol_ticker():
    assert safe("^JKSE") == "JKSE"
    assert safe("CL=F") == "CL_F"
    assert safe("IDR=X") == "IDR_X"


def test_local_sink_menulis_parquet(tmp_path):
    frame = pd.DataFrame({column: [1.0] for column in COLUMNS})
    frame["ticker"] = "^JKSE"

    sink = LocalSink(tmp_path)
    path = "bronze/prices/ticker=JKSE/ingest_date=2026-11-24/prices.parquet"
    sink.write_parquet(path, frame)

    target = tmp_path / path
    assert target.exists()
    assert len(pd.read_parquet(target)) == 1


def test_manifest_ditulis_sebagai_json(tmp_path):
    sink = LocalSink(tmp_path)
    sink.write_json("bronze/_manifest/ingest_date=2026-11-24/manifest.json", {"total_rows": 3})

    text = (tmp_path / "bronze/_manifest/ingest_date=2026-11-24/manifest.json").read_text(
        encoding="utf-8"
    )
    assert '"total_rows": 3' in text


@pytest.mark.parametrize("ticker", ["^JKSE", "CL=F", "IDR=X"])
def test_fetch_menolak_data_kosong(monkeypatch, ticker):
    """fetch() harus berhenti dengan IngestError, bukan mengembalikan tabel kosong."""
    from src import ingest

    class EmptyTicker:
        def history(self, **kwargs):
            return pd.DataFrame()

    monkeypatch.setattr(ingest.yf, "Ticker", lambda _: EmptyTicker())

    with pytest.raises(ingest.IngestError):
        ingest.fetch(ticker, "2026-01-01", retries=1)
