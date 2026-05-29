# API Data Pipeline

[![Python](https://img.shields.io/badge/Python-3.10+-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)]
[![Requests](https://img.shields.io/badge/Requests-2.28+-FF6F00?style=for-the-badge&logo=python&logoColor=white)]

Production-style data pipeline that extracts from public REST APIs, transforms, validates, and loads to CSV/Parquet/database.

## Features

- **Automatic pagination** — page-based, offset-based, with configurable max pages
- **Rate limiting** — configurable delay between API calls
- **Schema validation** — type coercion and required field checks
- **Data quality** — dedup, null imputation, string normalization
- **Multiple outputs** — CSV, JSON, Parquet, Feather, PostgreSQL
- **Pipeline metadata** — batch IDs, load timestamps, audit trail

## Usage

```bash
# From API with config
python api_pipeline.py --config examples/restcountries.json

# From file
python api_pipeline.py --source data.json --output data.parquet --type file

# Direct API call
python api_pipeline.py --source https://api.example.com/data --output output.csv
```

## Example Config

```json
{
  "source": "https://restcountries.com/v3.1/all",
  "output": "countries.parquet",
  "rate_limit": 0.5,
  "pagination": { "type": "page", "size": 100, "max_pages": 5 },
  "transforms": {
    "name": { "lower": true },
    "updated": { "date_parse": true }
  }
}
```

## Pipeline Stages

```
[API/File] → [Schema Validation] → [Cleaning] → [Transform] → [CSV/Parquet/DB]
```

## Author

**Koketso Raphasha** — [Kaggle](https://kaggle.com/Raphasha27) | [GitHub](https://github.com/Raphasha27)
