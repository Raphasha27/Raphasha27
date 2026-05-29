# Titanic ML - Kaggle Competition

[![Kaggle](https://img.shields.io/badge/Kaggle-Competition-20BEFF?style=for-the-badge&logo=kaggle)](https://www.kaggle.com/c/titanic)
![Python](https://img.shields.io/badge/Python-3.10+-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)

End-to-end machine learning solution for the Titanic: Machine Learning from Disaster competition on Kaggle. Features comprehensive EDA, feature engineering, model comparison, and ensemble stacking.

## Project Structure

```
titanic-ml/
├── titanic_kaggle.py          # v1 notebook-style script for Kaggle
├── titanic_kaggle_v2.py       # v2 optimized with hyperparameter tuning
├── submission.csv             # Generated predictions (83.2% estimated)
├── dashboard/                 # Streamlit interactive web app
│   ├── app.py
│   ├── requirements.txt
│   └── README.md
```

## Results

| Version | CV Accuracy | Validation Accuracy | Features |
|---------|:-----------:|:------------------:|----------|
| v1      | 82.6%       | 81.0%              | 14 features, 5 models, soft ensemble |
| v2      | **83.1%**   | **83.2%**          | 17 features, hyperparameter tuning, weighted ensemble |

## Approach

1. **Exploratory Data Analysis** — Visualize distributions, correlations, and missing values
2. **Feature Engineering** — Title extraction, family grouping, cabin decoding, age imputation, ticket prefix, fare-per-person
3. **Modeling** — Logistic Regression, Random Forest, XGBoost, Gradient Boosting, SVC
4. **Ensemble** — Weighted soft voting (weighted by CV performance)
5. **Submission** — Generate predictions in competition format

## Usage

```bash
pip install -r requirements.txt

# v1 (basic)
python titanic_kaggle.py

# v2 (optimized - recommended)
python titanic_kaggle_v2.py
```

## Author

**Koketso Raphasha** — [Kaggle](https://kaggle.com/Raphasha27)
