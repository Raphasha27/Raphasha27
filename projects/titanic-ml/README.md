# Titanic ML - Kaggle Competition

[![Kaggle](https://img.shields.io/badge/Kaggle-Competition-20BEFF?style=for-the-badge&logo=kaggle)](https://www.kaggle.com/c/titanic)
![Python](https://img.shields.io/badge/Python-3.10+-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)

End-to-end machine learning solution for the Titanic: Machine Learning from Disaster competition on Kaggle. Features comprehensive EDA, feature engineering, model comparison, and ensemble stacking.

## Project Structure

```
titanic-ml/
├── titanic_kaggle.py          # Main notebook-style script for Kaggle
├── README.md                  # This file
├── requirements.txt           # Dependencies
└── output/
    └── submission.csv         # Generated predictions
```

## Approach

1. **Exploratory Data Analysis** — Visualize distributions, correlations, and missing values
2. **Feature Engineering** — Title extraction, family grouping, cabin decoding, age imputation
3. **Modeling** — Random Forest, XGBoost, Logistic Regression, Gradient Boosting
4. **Ensemble** — Soft voting classifier combining top models
5. **Submission** — Generate predictions in competition format

## Usage

```bash
pip install -r requirements.txt
python titanic_kaggle.py
```

## Author

**Koketso Raphasha** — [Kaggle](https://kaggle.com/Raphasha27)
