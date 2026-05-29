"""
PySpark ETL Pipeline — Distributed Data Processing
====================================================
Stages: Ingest → Validate → Transform → Load → Report

Supports: CSV, Parquet, JSON, Avro
Modes: Local (standalone) or Cluster (YARN/K8s)

Usage:
    python spark_etl_pipeline.py --input data/ --output warehouse/
    spark-submit --master yarn spark_etl_pipeline.py --input s3a://bucket/in/
"""

import argparse
import json
import logging
import time
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger("SparkETL")


try:
    from pyspark.sql import SparkSession, DataFrame
    from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType, TimestampType
    from pyspark.sql.functions import (
        col, count, when, isnan, isnull, lit, md5, concat_ws,
        input_file_name, current_timestamp, avg, sum as spark_sum, desc
    )
    HAS_SPARK = True
except ImportError:
    HAS_SPARK = False
    logger.warning("PySpark not installed. Install with: pip install pyspark")


class SparkETLPipeline:
    """Production-grade PySpark ETL pipeline with data quality checks."""

    FORMAT_READERS = {
        ".csv": {"format": "csv", "options": {"header": "true", "inferSchema": "true", "multiLine": "true"}},
        ".parquet": {"format": "parquet", "options": {}},
        ".json": {"format": "json", "options": {"multiLine": "true"}},
    }

    def __init__(self, app_name: str = "Raphasha27_ETL", master: str = "local[*]"):
        if not HAS_SPARK:
            raise ImportError("PySpark is required. Run: pip install pyspark")
        self.spark = SparkSession.builder \
            .appName(app_name) \
            .master(master) \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.sql.adaptive.skewJoin.enabled", "true") \
            .getOrCreate()
        self.spark.sparkContext.setLogLevel("WARN")
        self.metrics = {
            "start_time": None, "end_time": None,
            "input_rows": 0, "output_rows": 0,
            "dropped_rows": 0, "duplicates": 0,
            "null_counts": {}, "partitions": 0,
        }
        logger.info("Spark session initialized: %s", app_name)

    def detect_format(self, path: str) -> str:
        ext = Path(path).suffix.lower() if not path.startswith("s3") else ".parquet"
        if ext in self.FORMAT_READERS:
            return ext
        return ".parquet"

    def ingest(self, path: str, schema: StructType = None) -> DataFrame:
        logger.info("Ingesting from: %s", path)
        ext = self.detect_format(path)
        reader_config = self.FORMAT_READERS.get(ext, self.FORMAT_READERS[".parquet"])

        reader = self.spark.read.format(reader_config["format"])
        for k, v in reader_config["options"].items():
            reader = reader.option(k, v)
        if schema:
            reader = reader.schema(schema)

        df = reader.load(path)
        self.metrics["input_rows"] = df.count()
        logger.info("Ingested %d rows, %d columns", self.metrics["input_rows"], len(df.columns))
        df.printSchema()
        return df

    def validate_quality(self, df: DataFrame, expected_cols: list = None) -> DataFrame:
        logger.info("Running data quality checks...")

        if expected_cols:
            actual_cols = set(df.columns)
            missing = set(expected_cols) - actual_cols
            if missing:
                logger.warning("Missing expected columns: %s", missing)

        null_checks = []
        for c in df.columns:
            null_count = df.filter(col(c).isNull() | isnan(c)).count()
            if null_count > 0:
                null_checks.append(f"  {c}: {null_count} nulls")
                self.metrics["null_counts"][c] = null_count
        if null_checks:
            logger.info("Null counts:\n%s", "\n".join(null_checks))
        else:
            logger.info("No null values found")

        return df

    def deduplicate(self, df: DataFrame, keys: list = None) -> DataFrame:
        before = df.count()
        if keys:
            df = df.dropDuplicates(keys)
        else:
            df = df.dropDuplicates()
        after = df.count()
        self.metrics["duplicates"] = before - after
        if self.metrics["duplicates"] > 0:
            logger.info("Removed %d duplicate rows", self.metrics["duplicates"])
        return df

    def transform(self, df: DataFrame) -> DataFrame:
        logger.info("Applying transformations...")

        df = df.withColumn("_etl_loaded_at", current_timestamp())

        str_cols = [c for c, t in df.dtypes if t == "string"]
        for c in str_cols:
            df = df.withColumn(c, when(col(c).isNull(), lit("Unknown")).otherwise(col(c)))
            df = df.withColumn(c, col(c).cast("string"))

        num_cols = [c for c, t in df.dtypes if t in ("double", "float", "int", "long")]
        for c in num_cols:
            median_val = df.approxQuantile(c, [0.5], 0.01)
            if median_val and len(median_val) > 0 and median_val[0] is not None:
                df = df.withColumn(c, when(col(c).isNull(), lit(median_val[0])).otherwise(col(c)))

        if "amount" in df.columns or "price" in df.columns:
            amount_col = "amount" if "amount" in df.columns else "price"
            df = df.withColumn("price_category",
                               when(col(amount_col) < 10, lit("low"))
                               .when(col(amount_col) < 100, lit("medium"))
                               .otherwise(lit("high")))

        df = df.withColumn("_record_hash", md5(concat_ws("||", *[col(c).cast("string") for c in df.columns if c != "_etl_loaded_at"])))

        self.metrics["output_rows"] = df.count()
        logger.info("Transform complete: %d rows output", self.metrics["output_rows"])
        return df

    def load(self, df: DataFrame, output_path: str, mode: str = "overwrite", partition_cols: list = None):
        logger.info("Loading to: %s (mode=%s)", output_path, mode)

        writer = df.write.format("parquet").mode(mode)

        if partition_cols:
            writer = writer.partitionBy(*partition_cols)

        writer.option("compression", "snappy").save(output_path)

        self.metrics["partitions"] = df.rdd.getNumPartitions()
        logger.info("Loaded %d rows across %d partitions", self.metrics["output_rows"], self.metrics["partitions"])

        df.write.format("parquet").mode("overwrite").option("compression", "snappy") \
            .save(str(Path(output_path).with_suffix(".parquet")))

    def report(self):
        elapsed = "N/A"
        if self.metrics["start_time"] and self.metrics["end_time"]:
            elapsed = f"{self.metrics['end_time'] - self.metrics['start_time']:.2f}s"

        print("\n" + "=" * 55)
        print("  PYSPARK ETL PIPELINE REPORT")
        print("=" * 55)
        print(f"  {'Input rows':20s}: {self.metrics['input_rows']}")
        print(f"  {'Output rows':20s}: {self.metrics['output_rows']}")
        print(f"  {'Duplicates removed':20s}: {self.metrics['duplicates']}")
        print(f"  {'Partitions':20s}: {self.metrics['partitions']}")
        print(f"  {'Elapsed':20s}: {elapsed}")
        if self.metrics["null_counts"]:
            print(f"  {'Columns with nulls':20s}: {len(self.metrics['null_counts'])}")
        print("=" * 55)

    def run(self, input_path: str, output_path: str, schema_path: str = None,
            partition_by: list = None, dedup_keys: list = None):
        logger.info("=" * 55)
        logger.info("PYSPARK ETL PIPELINE STARTED")
        logger.info("=" * 55)

        self.metrics["start_time"] = time.time()

        schema = None
        if schema_path:
            with open(schema_path) as f:
                schema_def = json.load(f)
            schema = StructType.fromJson(schema_def)

        df = self.ingest(input_path, schema)
        df = self.validate_quality(df)
        if dedup_keys is not None:
            df = self.deduplicate(df, dedup_keys)
        df = self.transform(df)
        self.load(df, output_path, partition_cols=partition_by)

        self.metrics["end_time"] = time.time()
        self.report()
        self.spark.stop()
        logger.info("PYSPARK ETL PIPELINE COMPLETED")
        return self.metrics


def main():
    parser = argparse.ArgumentParser(description="PySpark ETL Pipeline")
    parser.add_argument("--input", required=True, help="Input path (local, S3, HDFS)")
    parser.add_argument("--output", required=True, help="Output path for Parquet")
    parser.add_argument("--master", default="local[*]", help="Spark master URL")
    parser.add_argument("--schema", help="JSON schema file path")
    parser.add_argument("--partition-by", nargs="*", help="Columns to partition by")
    parser.add_argument("--dedup-keys", nargs="*", help="Columns for deduplication key")
    args = parser.parse_args()

    pipeline = SparkETLPipeline(master=args.master)
    pipeline.run(
        input_path=args.input,
        output_path=args.output,
        schema_path=args.schema,
        partition_by=args.partition_by,
        dedup_keys=args.dedup_keys,
    )


if __name__ == "__main__":
    main()
