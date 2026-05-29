"""
Production ETL Pipeline — CSV to PostgreSQL
=============================================
Stages: Extract → Validate → Clean → Transform → Load → Report

Usage:
    python etl_pipeline.py --input data.csv --table target_table --db-url postgresql://...
"""

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("etl_pipeline")


class ETLPipeline:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = create_engine(db_url) if db_url else None
        self.stats = {"rows_in": 0, "rows_out": 0, "dropped": 0, "duplicates": 0}

    def extract(self, filepath: str) -> pd.DataFrame:
        logger.info("Extracting: %s", filepath)
        path = Path(filepath)
        if path.suffix == ".csv":
            df = pd.read_csv(path)
        elif path.suffix in (".parquet", ".pq"):
            df = pd.read_parquet(path)
        elif path.suffix in (".xlsx", ".xls"):
            df = pd.read_excel(path)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
        self.stats["rows_in"] = len(df)
        logger.info("Extracted %d rows, %d cols", len(df), len(df.columns))
        return df

    def validate_schema(self, df: pd.DataFrame, expected_schema: dict = None):
        if expected_schema is None:
            logger.info("No schema constraints provided, skipping validation")
            return df
        for col, dtype in expected_schema.items():
            if col not in df.columns:
                logger.warning("Missing expected column: %s", col)
                continue
            if not pd.api.types.is_dtype_equal(df[col], dtype):
                logger.warning(
                    "Column %s: expected %s, got %s", col, dtype, df[col].dtype
                )
        return df

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Cleaning data...")
        before = len(df)

        df = df.drop_duplicates()
        dups = before - len(df)
        self.stats["duplicates"] = dups
        if dups:
            logger.info("Removed %d duplicate rows", dups)

        for col in df.select_dtypes(include=[np.number]).columns:
            null_count = df[col].isnull().sum()
            if null_count > 0:
                median_val = df[col].median()
                df[col] = df[col].fillna(median_val)
                logger.info(
                    "Filled %d nulls in '%s' with median %.2f", null_count, col, median_val
                )

        for col in df.select_dtypes(include=["object"]).columns:
            null_count = df[col].isnull().sum()
            if null_count > 0:
                df[col] = df[col].fillna("Unknown")
                logger.info("Filled %d nulls in '%s' with 'Unknown'", null_count, col)

        str_cols = df.select_dtypes(include=["object"]).columns
        df[str_cols] = df[str_cols].apply(lambda x: x.str.strip() if x.dtype == "object" else x)

        return df

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Applying transformations...")

        for col in df.select_dtypes(include=["object"]).columns:
            if df[col].nunique() < 20 and df[col].dtype == "object":
                df[col] = df[col].str.lower().str.replace(r"\s+", "_", regex=True)

        date_cols = [c for c in df.columns if "date" in c.lower() or "time" in c.lower()]
        for col in date_cols:
            try:
                df[col] = pd.to_datetime(df[col])
            except (ValueError, TypeError):
                pass

        df["_etl_loaded_at"] = datetime.utcnow()
        df["_etl_hash"] = df.apply(
            lambda row: hashlib.md5(
                str(row.to_dict()).encode()
            ).hexdigest(),
            axis=1,
        )

        logger.info("Transform complete — %d columns", len(df.columns))
        return df

    def load(self, df: pd.DataFrame, table: str, if_exists: str = "append"):
        if self.engine is None:
            logger.info("No DB configured — skipping load. Writing to parquet instead.")
            out_path = f"{table}_output.parquet"
            df.to_parquet(out_path, index=False)
            logger.info("Saved to %s", out_path)
            self.stats["rows_out"] = len(df)
            return

        logger.info("Loading %d rows into '%s'...", len(df), table)

        dtypes_map = {
            "int64": "BIGINT", "float64": "DOUBLE PRECISION",
            "object": "TEXT", "datetime64[ns]": "TIMESTAMP",
            "bool": "BOOLEAN",
        }
        col_types = {
            col: dtypes_map.get(str(dtype), "TEXT")
            for col, dtype in df.dtypes.items()
        }

        with self.engine.connect() as conn:
            conn.execute(text(f"CREATE TABLE IF NOT EXISTS {table} (_etl_id SERIAL PRIMARY KEY)"))
            for col, dtype in df.dtypes.items():
                sql_type = dtypes_map.get(str(dtype), "TEXT")
                try:
                    conn.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS \"{col}\" {sql_type}")
                    )
                except Exception:
                    pass
            conn.commit()

        df.to_sql(table, self.engine, if_exists=if_exists, index=False, method="multi")
        self.stats["rows_out"] = len(df)
        logger.info("Loaded %d rows into %s", len(df), table)

    def report(self):
        print("\n" + "=" * 50)
        print("ETL PIPELINE REPORT")
        print("=" * 50)
        for k, v in self.stats.items():
            print(f"  {k:15s}: {v}")
        print("=" * 50)
        if self.stats["rows_in"] > 0:
            pct = (self.stats["rows_out"] / self.stats["rows_in"]) * 100
            print(f"  Yield: {pct:.1f}% ({self.stats['rows_out']}/{self.stats['rows_in']})")
        print("=" * 50)

    def run(self, input_path: str, table: str, schema: dict = None):
        logger.info("=" * 50)
        logger.info("ETL PIPELINE STARTED")
        logger.info("=" * 50)
        df = self.extract(input_path)
        df = self.validate_schema(df, schema)
        df = self.clean(df)
        df = self.transform(df)
        self.load(df, table)
        self.report()
        logger.info("ETL PIPELINE COMPLETED")
        return self.stats


def main():
    parser = argparse.ArgumentParser(description="CSV to PostgreSQL ETL Pipeline")
    parser.add_argument("--input", required=True, help="Path to input file (CSV, Parquet, Excel)")
    parser.add_argument("--table", required=True, help="Target database table name")
    parser.add_argument("--db-url", help="PostgreSQL connection string (or set DB_URL env var)")
    parser.add_argument("--schema", help="JSON file with expected schema")
    args = parser.parse_args()

    db_url = args.db_url or os.getenv("DB_URL")
    schema = None
    if args.schema:
        with open(args.schema) as f:
            schema = json.load(f)

    pipeline = ETLPipeline(db_url)
    pipeline.run(args.input, args.table, schema)


if __name__ == "__main__":
    main()
