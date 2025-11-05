# MOPS Company Basic Data Crawler

This repository provides a Python script for collecting company basic data for the Taiwan Stock Exchange (上市), OTC (上櫃), and Emerging (興櫃) markets from the [MOPS website](https://mops.twse.com.tw/mops/#/web/t51sb01). The crawler performs the following steps:

1. Fetches company basic data for each market.
2. Aligns the resulting tables into a single Pandas DataFrame.
3. Converts the aligned DataFrame into an array of Python objects.
4. Saves the objects into a local MongoDB collection.

## Requirements

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

You also need access to a running MongoDB instance. The defaults assume MongoDB is available on `mongodb://localhost:27017`.

## Usage

Run the crawler script:

```bash
python -m src.mops_crawler --drop
```

Key arguments:

- `--mongo-uri`: MongoDB URI (default: `mongodb://localhost:27017`).
- `--database`: Database name (default: `mops`).
- `--collection`: Collection name (default: `companies`).
- `--drop`: Drop the target collection before inserting new data.
- `--log-level`: Python logging level (default: `INFO`).

The script fetches data for all three categories and upserts the results into MongoDB keyed by the company code (公司代號).

## Development Notes

- The script expects the `pandas`, `requests`, and `pymongo` packages to be available.
- The repository does not include automated tests; manual execution is recommended after configuring MongoDB access.
