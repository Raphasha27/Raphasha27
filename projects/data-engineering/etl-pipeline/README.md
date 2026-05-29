# ETL Pipeline — CSV to PostgreSQL

Production-style ETL pipeline that ingests CSV data, applies validation and cleaning, loads into PostgreSQL, and generates summary reports.

## Features

- Schema validation and data type coercion
- Missing value handling (imputation strategies)
- Duplicate detection and removal
- Audit logging for every pipeline run
- PostgreSQL upsert (ON CONFLICT) for idempotent loads
- Summary statistics and quality report output

## Usage

```bash
# Install dependencies
pip install pandas numpy sqlalchemy psycopg2-binary pyarrow

# Set environment variables
export DB_URL=postgresql://user:pass@localhost:5432/data_warehouse

# Run pipeline
python etl_pipeline.py --input data/orders.csv --table orders
```

## Pipeline Stages

```
[CSV Source] → [Validation] → [Cleaning] → [Transformation] → [Load to PostgreSQL] → [Report]
```

## Author

**Koketso Raphasha** — Data Engineer
