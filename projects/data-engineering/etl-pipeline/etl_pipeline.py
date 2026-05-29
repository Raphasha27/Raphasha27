"""
Production ETL Pipeline v2 — CSV to PostgreSQL with advanced validation
=======================================================================
Stages: Extract → Profile → Validate → Clean → Transform → Load → Report
Features: Config file, batch processing, data profiling, CSV dialect detection, schema evolution

Usage:
    python etl_pipeline.py --config pipeline_config.json
    python etl_pipeline.py --input data.csv --table target --db-url postgresql://...
"""

import argparse
import csv
import hashlib
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text, inspect

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("etl_pipeline_v2")


class ETLPipeline:
    def __init__(self, db_url: str = None, config: dict = None):
        self.config = config or {}
        self.db_url = db_url or self.config.get("db_url") or os.getenv("DB_URL")
        self.engine = create_engine(self.db_url) if self.db_url else None
        self.batch_size = self.config.get("batch_size", 10000)
        self.strict_mode = self.config.get("strict_mode", False)
        self.stats = {
            "rows_in": 0, "rows_out": 0, "dropped": 0, "duplicates": 0,
            "null_filled": 0, "validation_errors": 0, "start_time": None, "end_time": None,
        }

    def extract(self, filepath: str) -> pd.DataFrame:
        logger.info("Extracting: %s", filepath)
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {filepath}")

        try:
            if path.suffix == ".csv":
                dialect = self._detect_csv_dialect(filepath)
                df = pd.read_csv(path, dialect=dialect, low_memory=False)
            elif path.suffix in (".parquet", ".pq"):
                df = pd.read_parquet(path)
            elif path.suffix in (".xlsx", ".xls"):
                df = pd.read_excel(path, sheet_name=self.config.get("sheet_name", 0))
            elif path.suffix == ".json":
                df = pd.read_json(path, lines=self.config.get("json_lines", False))
            elif path.suffix == ".feather":
                df = pd.read_feather(path)
            else:
                raise ValueError(f"Unsupported file format: {path.suffix}")
        except Exception as e:
            logger.error("Extraction failed: %s", e)
            raise

        self.stats["rows_in"] = len(df)
        logger.info("Extracted %d rows, %d cols | Memory: %.1f MB",
                     len(df), len(df.columns), df.memory_usage(deep=True).sum() / 1e6)
        return df

    def _detect_csv_dialect(self, filepath: str) -> csv.Dialect:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            sample = f.read(8192)
        try:
            dialect = csv.Sniffer().sniff(sample)
            logger.info("Detected CSV dialect: delimiter='%s' quote='%s'", dialect.delimiter, dialect.quotechar)
            return dialect
        except csv.Error:
            logger.info("Using default CSV dialect (comma-delimited)")
            return csv.excel()

    def profile(self, df: pd.DataFrame) -> dict:
        logger.info("Profiling data...")
        profile = {
            "rows": len(df),
            "columns": len(df.columns),
            "dtypes": {c: str(d) for c, d in df.dtypes.items()},
            "nulls": {c: int(df[c].isnull().sum()) for c in df.columns},
            "uniques": {c: int(df[c].nunique()) for c in df.columns if df[c].dtype == "object"},
            "numeric_stats": {},
        }
        for c in df.select_dtypes(include=[np.number]).columns:
            profile["numeric_stats"][c] = {
                "min": float(df[c].min()) if df[c].notna().any() else None,
                "max": float(df[c].max()) if df[c].notna().any() else None,
                "mean": float(df[c].mean()) if df[c].notna().any() else None,
                "std": float(df[c].std()) if df[c].notna().any() else None,
            }
        logger.info("Profile: %d cols, %d rows, %d columns with nulls",
                     profile["columns"], profile["rows"], sum(1 for v in profile["nulls"].values() if v > 0))
        return profile

    def validate_schema(self, df: pd.DataFrame, expected_schema: dict = None) -> pd.DataFrame:
        if expected_schema is None:
            expected_schema = self.config.get("schema", {})
        if not expected_schema:
            logger.info("No schema constraints — skipping validation")
            return df

        errors = []
        for col, rules in expected_schema.items():
            if col not in df.columns:
                msg = f"Missing column: {col}"
                if self.strict_mode:
                    raise ValueError(msg)
                logger.warning(msg)
                continue

            dtype = rules.get("dtype")
            if dtype and not pd.api.types.is_dtype_equal(df[col], dtype):
                logger.warning("Column %s: expected dtype %s, got %s", col, dtype, df[col].dtype)

            min_val = rules.get("min")
            max_val = rules.get("max")
            if min_val is not None and df[col].dtype in (int, float, np.number):
                outliers = df[df[col] < min_val].shape[0]
                if outliers:
                    logger.warning("Column %s: %d values below min %s", col, outliers, min_val)

            nullable = rules.get("nullable", True)
            if not nullable:
                nulls = int(df[col].isnull().sum())
                if nulls > 0:
                    msg = f"Column {col}: {nulls} nulls (expected non-nullable)"
                    if self.strict_mode:
                        raise ValueError(msg)
                    logger.warning(msg)

        if errors:
            self.stats["validation_errors"] += len(errors)
        return df

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Cleaning data...")
        before = len(df)

        df = df.drop_duplicates()
        dups = before - len(df)
        self.stats["duplicates"] = dups
        if dups:
            logger.info("Removed %d duplicate rows", dups)

        null_filled = 0
        for col in df.select_dtypes(include=[np.number]).columns:
            null_count = int(df[col].isnull().sum())
            if null_count > 0:
                impute_val = self.config.get("impute", {}).get(col, df[col].median())
                df[col] = df[col].fillna(impute_val)
                null_filled += null_count
                logger.info("Filled %d nulls in '%s' with %.2f", null_count, col, impute_val)

        for col in df.select_dtypes(include=["object"]).columns:
            null_count = int(df[col].isnull().sum())
            if null_count > 0:
                fill_val = self.config.get("impute", {}).get(col, "Unknown")
                df[col] = df[col].fillna(fill_val)
                null_filled += null_count
                logger.info("Filled %d nulls in '%s' with '%s'", null_count, col, fill_val)

        self.stats["null_filled"] = null_filled

        str_cols = df.select_dtypes(include=["object"]).columns
        df[str_cols] = df[str_cols].apply(lambda x: x.str.strip() if x.dtype == "object" else x)

        return df

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Applying transformations...")

        for col in df.select_dtypes(include=["object"]).columns:
            if df[col].nunique() < 20 and df[col].dtype == "object":
                df[col] = df[col].str.lower().str.replace(r"\s+", "_", regex=True)

        date_cols = [c for c in df.columns if any(k in c.lower() for k in ("date", "time", "updated", "created"))]
        for col in date_cols:
            try:
                df[col] = pd.to_datetime(df[col], errors="coerce")
            except (ValueError, TypeError):
                pass

        df["_etl_loaded_at"] = datetime.utcnow()
        df["_etl_batch_id"] = hashlib.md5(str(time.time()).encode()).hexdigest()[:12]
        hash_cols = [c for c in df.columns if c not in ("_etl_loaded_at", "_etl_batch_id", "_etl_hash")]
        df["_etl_hash"] = df[hash_cols].apply(
            lambda row: hashlib.sha256(str(row.to_dict()).encode()).hexdigest(), axis=1
        )

        logger.info("Transform complete — %d columns, hash=%s", len(df.columns), df["_etl_batch_id"].iloc[0])
        return df

    def load(self, df: pd.DataFrame, table: str, if_exists: str = "append"):
        if self.engine is None:
            logger.info("No DB configured — writing to parquet")
            out_path = self.config.get("fallback_path", f"{table}_output.parquet")
            df.to_parquet(out_path, index=False, compression="snappy")
            logger.info("Saved %d rows to %s", len(df), out_path)
            self.stats["rows_out"] = len(df)
            return

        logger.info("Loading %d rows into '%s' (batch_size=%d)...", len(df), table, self.batch_size)

        dtypes_map = {
            "int64": "BIGINT", "float64": "DOUBLE PRECISION",
            "object": "TEXT", "datetime64[ns]": "TIMESTAMP",
            "bool": "BOOLEAN", "int32": "INTEGER", "float32": "REAL",
        }

        with self.engine.connect() as conn:
            conn.execute(text(f"CREATE TABLE IF NOT EXISTS {table} (_etl_id SERIAL PRIMARY KEY, _etl_batch_id TEXT)"))
            existing_cols = set(row[0] for row in conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}'")).fetchall())
            for col, dtype in df.dtypes.items():
                if col not in existing_cols:
                    sql_type = dtypes_map.get(str(dtype), "TEXT")
                    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS "{col}" {sql_type}'))
            conn.commit()

        df.to_sql(table, self.engine, if_exists=if_exists, index=False, method="multi", chunksize=self.batch_size)
        self.stats["rows_out"] = len(df)
        logger.info("Loaded %d rows into %s", len(df), table)

    def report(self):
        elapsed = "N/A"
        if self.stats["start_time"] and self.stats["end_time"]:
            elapsed = f"{self.stats['end_time'] - self.stats['start_time']:.2f}s"

        print("\n" + "=" * 55)
        print("  ETL PIPELINE REPORT — v2")
        print("=" * 55)
        print(f"  {'Rows in':20s}: {self.stats['rows_in']}")
        print(f"  {'Rows out':20s}: {self.stats['rows_out']}")
        print(f"  {'Duplicates removed':20s}: {self.stats['duplicates']}")
        print(f"  {'Nulls filled':20s}: {self.stats['null_filled']}")
        print(f"  {'Validation errors':20s}: {self.stats['validation_errors']}")
        print(f"  {'Dropped':20s}: {self.stats['dropped']}")
        print(f"  {'Elapsed':20s}: {elapsed}")
        if self.stats["rows_in"] > 0:
            pct = (self.stats["rows_out"] / self.stats["rows_in"]) * 100 if self.stats["rows_in"] else 0
            print(f"  {'Yield':20s}: {pct:.1f}% ({self.stats['rows_out']}/{self.stats['rows_in']})")
        print("=" * 55)

    def run(self, input_path: str = None, table: str = None, schema: dict = None):
        self.stats["start_time"] = time.time()

        input_path = input_path or self.config.get("input")
        table = table or self.config.get("table")
        schema = schema or self.config.get("schema")

        if not input_path:
            raise ValueError("No input path provided")
        if not table:
            raise ValueError("No target table provided")

        logger.info("=" * 55)
        logger.info("ETL PIPELINE v2 STARTED")
        logger.info("=" * 55)

        df = self.extract(input_path)
        self.profile(df)
        df = self.validate_schema(df, schema)
        df = self.clean(df)
        df = self.transform(df)
        self.load(df, table)

        self.stats["end_time"] = time.time()
        self.report()
        logger.info("ETL PIPELINE COMPLETED")
        return self.stats

    def run_batch(self, inputs: list):
        """Process multiple input files, loading to same table."""
        for i, inp in enumerate(inputs):
            logger.info("--- Batch %d/%d ---", i + 1, len(inputs))
            self.run(input_path=inp, table=self.config.get("table"))


def main():
    parser = argparse.ArgumentParser(description="ETL Pipeline v2 — CSV to PostgreSQL")
    parser.add_argument("--input", help="Path to input file")
    parser.add_argument("--table", help="Target database table name")
    parser.add_argument("--db-url", help="PostgreSQL connection string")
    parser.add_argument("--config", help="JSON config file")
    parser.add_argument("--strict", action="store_true", help="Strict validation mode")
    args = parser.parse_args()

    config = None
    if args.config:
        with open(args.config) as f:
            config = json.load(f)
        logger.info("Loaded config from %s", args.config)

    db_url = args.db_url or (config.get("db_url") if config else None) or os.getenv("DB_URL")

    pipeline = ETLPipeline(db_url=db_url, config=config)
    if config and not args.strict:
        pipeline.strict_mode = config.get("strict_mode", False)
    if args.strict:
        pipeline.strict_mode = True

    inputs = config.get("inputs", [args.input]) if config and not args.input else [args.input]
    if len(inputs) > 1:
        pipeline.run_batch(inputs)
    else:
        pipeline.run(input_path=inputs[0], table=args.table or (config.get("table") if config else None))


if __name__ == "__main__":
    main()
