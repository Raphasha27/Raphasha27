"""
API Data Pipeline — Public API → Transform → Load
====================================================
Pipeline: Extract (API) → Validate → Transform → Load (CSV/Parquet/DB)
Features: Rate limiting, pagination, caching, schema validation, data quality reports

Usage:
    python api_pipeline.py --config config.json
    python api_pipeline.py --url https://api.example.com/data --output data.parquet
"""

import argparse
import hashlib
import json
import logging
import os
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

import numpy as np
import pandas as pd
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("api_pipeline")


class APIDataPipeline:
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Raphasha27-DataPipeline/1.0",
            "Accept": "application/json",
        })
        self.rate_limit = self.config.get("rate_limit", 1.0)  # seconds between requests
        self.last_request = 0
        self.stats = {
            "rows_extracted": 0, "rows_loaded": 0,
            "api_calls": 0, "api_errors": 0,
            "start_time": None, "end_time": None,
            "duplicates_removed": 0, "nulls_filled": 0,
        }
        api_key = self.config.get("api_key") or os.getenv(self.config.get("api_key_env", "API_KEY"))
        if api_key:
            self.session.headers.update(self.config.get("auth_header", {"Authorization": f"Bearer {api_key}"}))

    def _rate_limit(self):
        elapsed = time.time() - self.last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request = time.time()

    def extract_from_api(self, url: str, params: dict = None, pagination: dict = None) -> pd.DataFrame:
        logger.info("Extracting from API: %s", url)
        all_records = []
        page = 1
        params = params or {}
        pagination = pagination or self.config.get("pagination", {})

        while True:
            self._rate_limit()
            page_params = {**params}

            if pagination.get("type") == "page":
                page_params[pagination.get("param", "page")] = page
                page_params[pagination.get("size_param", "per_page")] = pagination.get("size", 100)
            elif pagination.get("type") == "offset":
                page_params[pagination.get("param", "offset")] = (page - 1) * pagination.get("size", 100)
                page_params[pagination.get("limit_param", "limit")] = pagination.get("size", 100)

            try:
                resp = self.session.get(url, params=page_params, timeout=self.config.get("timeout", 30))
                self.stats["api_calls"] += 1
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as e:
                self.stats["api_errors"] += 1
                logger.error("API error (page %d): %s", page, e)
                if self.config.get("strict", False):
                    raise
                break

            records = data
            if pagination.get("results_path"):
                for key in pagination["results_path"].split("."):
                    if isinstance(records, dict):
                        records = records.get(key, [])
                    else:
                        records = []

            if not isinstance(records, list):
                records = [records]

            if not records:
                break

            all_records.extend(records)
            logger.info("Page %d: %d records (total: %d)", page, len(records), len(all_records))

            has_more = True
            if pagination.get("type") == "page":
                total_pages = data.get(pagination.get("total_pages_field", "total_pages"), 0) if isinstance(data, dict) else 0
                has_more = page < total_pages if total_pages else len(records) >= pagination.get("size", 100)
            elif pagination.get("type") == "offset":
                has_more = len(records) >= pagination.get("size", 100)

            if not has_more or (pagination.get("max_pages") and page >= pagination["max_pages"]):
                break
            page += 1

        df = pd.DataFrame(all_records)
        self.stats["rows_extracted"] = len(df)
        logger.info("Extracted %d rows, %d columns from API", len(df), len(df.columns))
        return df

    def extract_from_file(self, filepath: str) -> pd.DataFrame:
        logger.info("Extracting from file: %s", filepath)
        path = Path(filepath)
        if path.suffix == ".csv":
            df = pd.read_csv(path)
        elif path.suffix in (".json", ".jsonl"):
            df = pd.read_json(path, lines=path.suffix == ".jsonl")
        elif path.suffix in (".parquet", ".pq"):
            df = pd.read_parquet(path)
        else:
            raise ValueError(f"Unsupported format: {path.suffix}")
        self.stats["rows_extracted"] = len(df)
        return df

    def validate_schema(self, df: pd.DataFrame, schema: dict = None) -> pd.DataFrame:
        schema = schema or self.config.get("schema", {})
        if not schema:
            logger.info("No schema — skipping validation")
            return df

        for col, rules in schema.items():
            if col not in df.columns:
                if rules.get("required", False):
                    logger.warning("Missing required column: %s", col)
                continue
            dtype = rules.get("dtype")
            if dtype:
                try:
                    df[col] = df[col].astype(dtype)
                except (ValueError, TypeError):
                    logger.warning("Could not cast %s to %s", col, dtype)
        return df

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Cleaning data...")
        before = len(df)
        df = df.drop_duplicates()
        self.stats["duplicates_removed"] = before - len(df)
        if self.stats["duplicates_removed"]:
            logger.info("Removed %d duplicates", self.stats["duplicates_removed"])

        nulls_filled = 0
        for col in df.select_dtypes(include=[np.number]).columns:
            n = int(df[col].isnull().sum())
            if n:
                df[col] = df[col].fillna(df[col].median())
                nulls_filled += n
        for col in df.select_dtypes(include=["object"]).columns:
            n = int(df[col].isnull().sum())
            if n:
                df[col] = df[col].fillna("Unknown")
                nulls_filled += n
        self.stats["nulls_filled"] = nulls_filled
        return df

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Applying transformations...")
        transforms = self.config.get("transforms", {})

        for col, ops in transforms.items():
            if col not in df.columns:
                continue

            if "date_parse" in ops and ops["date_parse"]:
                try:
                    df[col] = pd.to_datetime(df[col])
                except (ValueError, TypeError):
                    pass

            if "lower" in ops and ops["lower"]:
                df[col] = df[col].astype(str).str.lower()

            if "rename" in ops:
                df = df.rename(columns={col: ops["rename"]})

            if "extract" in ops:
                df[ops["extract"]["new_col"]] = df[col].str.extract(ops["extract"]["pattern"], expand=False)

        if transforms.get("_add_metadata", True):
            df["_pipeline_loaded_at"] = datetime.utcnow()
            df["_pipeline_batch"] = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]

        if transforms.get("_normalize_strings", True):
            for col in df.select_dtypes(include=["object"]).columns:
                df[col] = df[col].astype(str).str.strip()

        self.stats["rows_loaded"] = len(df)
        logger.info("Transform complete: %d rows", len(df))
        return df

    def load(self, df: pd.DataFrame, output_path: str):
        logger.info("Loading to: %s", output_path)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.suffix == ".csv":
            df.to_csv(path, index=False)
        elif path.suffix == ".json":
            df.to_json(path, orient="records", indent=2)
        elif path.suffix == ".parquet":
            df.to_parquet(path, index=False, compression="snappy")
        elif path.suffix == ".feather":
            df.to_feather(path)
        else:
            df.to_parquet(path.with_suffix(".parquet"), index=False)

        logger.info("Loaded %d rows to %s", len(df), path)

        if self.config.get("load_to_db"):
            try:
                from sqlalchemy import create_engine
                db_url = self.config["load_to_db"] or os.getenv("DB_URL")
                if db_url:
                    engine = create_engine(db_url)
                    table = self.config.get("table", path.stem)
                    df.to_sql(table, engine, if_exists="append", index=False, method="multi")
                    logger.info("Also loaded to DB table: %s", table)
            except Exception as e:
                logger.warning("DB load skipped: %s", e)

    def report(self):
        elapsed = "N/A"
        if self.stats["start_time"] and self.stats["end_time"]:
            elapsed = f"{self.stats['end_time'] - self.stats['start_time']:.2f}s"

        print("\n" + "=" * 55)
        print("  API DATA PIPELINE REPORT")
        print("=" * 55)
        print(f"  {'Rows extracted':20s}: {self.stats['rows_extracted']}")
        print(f"  {'Rows loaded':20s}: {self.stats['rows_loaded']}")
        print(f"  {'API calls':20s}: {self.stats['api_calls']}")
        print(f"  {'API errors':20s}: {self.stats['api_errors']}")
        print(f"  {'Duplicates removed':20s}: {self.stats['duplicates_removed']}")
        print(f"  {'Nulls filled':20s}: {self.stats['nulls_filled']}")
        print(f"  {'Elapsed':20s}: {elapsed}")
        print("=" * 55)

    def run(self, source: str = None, output: str = None, source_type: str = "api"):
        self.stats["start_time"] = time.time()
        source = source or self.config.get("source")
        output = output or self.config.get("output")
        if not source or not output:
            raise ValueError("source and output are required")

        logger.info("=" * 55)
        logger.info("API DATA PIPELINE STARTED")
        logger.info("=" * 55)

        if source_type == "api":
            df = self.extract_from_api(source, pagination=self.config.get("pagination"))
        else:
            df = self.extract_from_file(source)

        df = self.validate_schema(df)
        df = self.clean(df)
        df = self.transform(df)
        self.load(df, output)

        self.stats["end_time"] = time.time()
        self.report()
        logger.info("API DATA PIPELINE COMPLETED")
        return self.stats


def main():
    parser = argparse.ArgumentParser(description="API Data Pipeline")
    parser.add_argument("--source", help="API URL or file path")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--config", help="JSON config file")
    parser.add_argument("--type", choices=["api", "file"], default="api", help="Source type")
    args = parser.parse_args()

    config = None
    if args.config:
        with open(args.config) as f:
            config = json.load(f)
        logger.info("Loaded config: %s", args.config)

    pipeline = APIDataPipeline(config)
    pipeline.run(source=args.source, output=args.output, source_type=args.type)


if __name__ == "__main__":
    main()
