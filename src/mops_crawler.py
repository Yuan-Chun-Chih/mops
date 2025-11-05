"""Crawler for MOPS company basic data.

Steps implemented:
1. Fetch company basic data for listed, OTC, and emerging boards.
2. Align DataFrame columns across all categories.
3. Convert the aligned DataFrame into a list of objects.
4. Persist the result into a MongoDB collection.
"""
from __future__ import annotations

import argparse
import logging
from typing import Dict, Iterable, List

import pandas as pd
import requests
from pandas import DataFrame
from pymongo import MongoClient
from pymongo.collection import Collection

MOPS_URL = "https://mops.twse.com.tw/mops/web/ajax_t51sb01"
CATEGORY_CODES = {
    "listed": "sii",   # 上市
    "otc": "otc",      # 上櫃
    "emerging": "rotc",  # 興櫃
}


def fetch_company_table(session: requests.Session, category: str, code: str) -> DataFrame:
    """Fetch the company table for the given MOPS category.

    Parameters
    ----------
    session:
        An existing :class:`requests.Session` used to perform the HTTP request.
    category:
        The user visible category name (listed/otc/emerging). Used only for logging.
    code:
        The TYPEK value expected by the MOPS backend (e.g. "sii").

    Returns
    -------
    pandas.DataFrame
        The parsed DataFrame containing the company basic information table.
    """
    payload = {
        "encodeURIComponent": "1",
        "step": "1",
        "firstin": "1",
        "TYPEK": code,
        "code": "",
    }
    logging.info("Fetching %s companies", category)
    response = session.post(MOPS_URL, data=payload, timeout=30)
    response.raise_for_status()

    tables = pd.read_html(response.text)
    for table in tables:
        if "公司代號" in table.columns:
            table = table.copy()
            table["市場別"] = category
            return table

    raise ValueError(f"Unable to locate company table for category '{category}'")


def align_tables(tables: Iterable[DataFrame]) -> DataFrame:
    """Align multiple company tables into a single DataFrame with unified columns."""
    frames: List[DataFrame] = []
    all_columns: List[str] = []

    for table in tables:
        frames.append(table)
        for column in table.columns:
            if column not in all_columns:
                all_columns.append(column)

    aligned_frames = [frame.reindex(columns=all_columns) for frame in frames]
    combined = pd.concat(aligned_frames, ignore_index=True)
    return combined


def dataframe_to_objects(df: DataFrame) -> List[Dict[str, object]]:
    """Convert the DataFrame into a list of dictionaries (objects)."""
    # Replace pandas specific NaN values with None to create clean MongoDB documents.
    cleansed = df.where(pd.notnull(df), None)
    records: List[Dict[str, object]] = cleansed.to_dict(orient="records")
    return records


def persist_to_mongo(collection: Collection, documents: List[Dict[str, object]], *, key: str = "公司代號") -> None:
    """Persist the documents into MongoDB using an upsert on the provided key."""
    logging.info("Saving %s documents into MongoDB collection %s", len(documents), collection.full_name)
    for doc in documents:
        identifier = doc.get(key)
        if identifier is None:
            logging.warning("Skipping document without key '%s': %s", key, doc)
            continue
        collection.replace_one({key: identifier}, doc, upsert=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch company basics from MOPS and store into MongoDB.")
    parser.add_argument(
        "--mongo-uri",
        default="mongodb://localhost:27017",
        help="MongoDB connection URI (default: %(default)s)",
    )
    parser.add_argument(
        "--database",
        default="mops",
        help="MongoDB database name (default: %(default)s)",
    )
    parser.add_argument(
        "--collection",
        default="companies",
        help="MongoDB collection name (default: %(default)s)",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop the target collection before inserting documents.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (default: %(default)s)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))

    session = requests.Session()
    tables = []
    for category, code in CATEGORY_CODES.items():
        table = fetch_company_table(session, category, code)
        tables.append(table)

    aligned = align_tables(tables)
    documents = dataframe_to_objects(aligned)

    client = MongoClient(args.mongo_uri)
    db = client[args.database]
    collection = db[args.collection]

    if args.drop:
        logging.info("Dropping collection %s before inserting", collection.full_name)
        collection.drop()

    persist_to_mongo(collection, documents)
    logging.info("Completed successfully")


if __name__ == "__main__":
    main()
