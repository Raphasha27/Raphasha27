# PySpark ETL Pipeline — Big Data Processing

[![Spark](https://img.shields.io/badge/Spark-3.5+-E25A1C?style=for-the-badge&logo=apache-spark&logoColor=white)](https://spark.apache.org/)
[![Python](https://img.shields.io/badge/Python-3.10+-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)]

Production-scale ETL pipeline using Apache PySpark for processing large datasets with distributed computing.

## Features

- **Distributed Processing** — PySpark DataFrame API for large-scale data
- **Multi-format Support** — CSV, Parquet, JSON, Avro, Delta Lake
- **Data Quality Checks** — Null detection, duplicate removal, schema validation
- **Incremental Loads** — Append/overwrite modes with partition pruning
- **Performance Optimizations** — Partitioning, bucketing, broadcast joins
- **Metrics & Reporting** — Row counts, processing time, data quality stats

## Pipeline Stages

```
[Source: HDFS/S3/GCS]
    ↓
[Ingestion: CSV/Parquet/JSON]
    ↓
[Validation: Schema + Nulls + Dups]
    ↓
[Transform: Clean → Enrich → Aggregate]
    ↓
[Load: Parquet/Delta → HDFS/S3]
    ↓
[Report: Metrics & Quality Dashboard]
```

## Usage

```bash
# Local mode
python spark_etl_pipeline.py --input data/transactions.csv --output data/warehouse

# Cluster mode
spark-submit \
  --master yarn \
  --deploy-mode cluster \
  --num-executors 10 \
  spark_etl_pipeline.py \
  --input s3a://bucket/input/ \
  --output s3a://bucket/warehouse/
```

## Author

**Koketso Raphasha** — [Kaggle](https://kaggle.com/Raphasha27)
