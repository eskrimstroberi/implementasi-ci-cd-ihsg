# Implementasi CI/CD Pipeline Ingestion Data IHSG

Pipeline ingestion data harian delapan instrumen IHSG memakai `yfinance`, disimpan
sebagai Parquet di Azure Blob Storage, dijalankan otomatis setiap 6 jam oleh
GitHub Actions.

## Arsitektur

```
Yahoo Finance (8 ticker)
        |
        v
src/ingest.py  ->  src/main.py  ->  sink
                                     |-- local: ./data
                                     '-- Azure Blob: bronze/prices/...
```

Struktur blob:

```
bronze/prices/ticker=JKSE/ingest_date=2026-11-24/prices.parquet
bronze/prices/ticker=CL_F/ingest_date=2026-11-24/prices.parquet
...
bronze/_manifest/ingest_date=2026-11-24/manifest.json
```

Manifest mencatat tanggal acuan, waktu jalan (UTC), versi `yfinance`, jumlah baris,
rentang tanggal, dan SHA-256 isi tiap tabel.

## Instrumen

| Simbol | Instrumen | Peran |
|---|---|---|
| ^JKSE | IHSG | objek prediksi |
| CL=F | Minyak mentah WTI | faktor komoditas |
| GC=F | Emas | aset lindung nilai |
| IDR=X | Kurs USD/IDR | faktor nilai tukar |
| ^HSI | Hang Seng | indeks regional |
| ^N225 | Nikkei 225 | indeks regional |
| ^DJI | Dow Jones | indeks global |
| EEM | ETF pasar berkembang | proksi aliran modal |

## Menjalankan lokal

```bash
pip install -r requirements.txt
python -m src.main --local
ruff check src tests
pytest -q
```

Hasil ditulis ke `data/bronze/...` tanpa menyentuh Azure.

## Menjalankan ke Azure

Lokal (memakai sesi `az login`):

```bash
az login
export AZURE_STORAGE_ACCOUNT=stihsgmeiva02224044
export AZURE_STORAGE_CONTAINER=ihsg-lake
python -m src.main
python -m src.verify
```

Di GitHub Actions kredensial diambil lewat **federated credential (OIDC)**:
`azure/login@v2` menukar token GitHub dengan token Azure, sehingga tidak ada
client secret maupun access key yang disimpan di repository.

## Workflow

- `.github/workflows/ci.yml` — pada push/PR ke `dev` dan `main`: Ruff, Pytest,
  dan smoke test pipeline ke folder lokal.
- `.github/workflows/pipeline.yml` — pada jadwal `0 */6 * * *` dan manual:
  login Azure, ingestion ke Blob, verifikasi 8 ticker, unggah manifest sebagai artifact.

Catatan: cron GitHub Actions memakai UTC. `0 */6 * * *` berarti pukul 07, 13, 19,
dan 01 WIB.

## Konfigurasi di GitHub

Settings → Secrets and variables → Actions → tab **Variables**:

| Nama | Isi |
|---|---|
| `AZURE_CLIENT_ID` | `72eb20b8-b312-46f0-a048-2e6db980b1b2` |
| `AZURE_TENANT_ID` | `50ffc1ca-cc7e-4aa2-a926-4564869b5b26` |
| `AZURE_SUBSCRIPTION_ID` | `f9c2eb8b-8826-4460-a53c-0455ec2f86ce` |
| `AZURE_STORAGE_ACCOUNT` | `stihsgmeiva02224044` |
| `AZURE_STORAGE_CONTAINER` | `ihsg-lake` |

## Resource Azure yang dipakai

| Komponen | Nama |
|---|---|
| Resource Group | `rg-ihsg-cicd` (Southeast Asia) |
| Storage Account | `stihsgmeiva02224044` (ADLS Gen2, hierarchical namespace aktif, East Asia) |
| Container | `ihsg-lake` |
| App Registration | `ihsg-github-actions` |
| Federated credential | `github-actions-ihsg-main` (branch `main`) |
| Role | `Storage Blob Data Contributor` pada Storage Account |
