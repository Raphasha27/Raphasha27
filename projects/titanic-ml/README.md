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
├── titanic_kaggle_v3.py       # v3 stacking ensemble + meta learner
├── submission.csv             # Generated predictions
├── dashboard/                 # Streamlit interactive web app
│   ├── app.py
│   ├── requirements.txt
│   └── README.md
```

## Results

| Version | CV Accuracy | Kaggle LB | Approach |
|---------|:-----------:|:---------:|----------|
| v1      | 82.6%       | —         | 5-model soft ensemble, 14 features |
| v2      | 83.1%       | 76.3%     | Hyperparameter tuning, weighted ensemble, 17 features |
| v3      | **83.5%**   | **79.0%** | Stacking (7 models + meta LR), 13 robust features, full 891 train |

## Approach

1. **Exploratory Data Analysis** — Visualize distributions, correlations, and missing values
2. **Feature Engineering** — Title extraction, family grouping, cabin decoding, age imputation
3. **Modeling** — 7 base models with 10-fold cross-validation (LR, Ridge, RF, GB, ET, XGB, KNN)
4. **Stacking** — LogisticRegression meta-learner trained on OOF probabilities
5. **Submission** — Generate predictions leveraging all 891 training samples

## Usage

```bash
pip install -r requirements.txt

# v1 (basic)
python titanic_kaggle.py

# v2 (optimized)
python titanic_kaggle_v2.py

# v3 (best - stacking ensemble)
python titanic_kaggle_v3.py
```

## Author

**Koketso Raphasha** — [Kaggle](https://kaggle.com/Raphasha27)
