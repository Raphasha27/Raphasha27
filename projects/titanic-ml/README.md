# Titanic ML - Kaggle Competition

[![Kaggle](https://img.shields.io/badge/Kaggle-Competition-20BEFF?style=for-the-badge&logo=kaggle)](https://www.kaggle.com/c/titanic)
![Python](https://img.shields.io/badge/Python-3.10+-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)

End-to-end machine learning solution for the Titanic: Machine Learning from Disaster competition on Kaggle. Features comprehensive EDA, feature engineering, model comparison, and ensemble stacking.

## Project Structure

```
titanic-ml/
├── titanic_kaggle.py          # v1 notebook-style script
├── titanic_kaggle_v2.py       # v2 hyperparameter tuning, weighted ensemble
├── titanic_kaggle_v3.py       # v3 stacking (7 models + meta LR)
├── titanic_kaggle_v4.py       # v4 KNN impute + interaction features (77.5%)
├── titanic_kaggle_v5.py       # v5 23 features, 8-model blend
├── titanic_kaggle_v6.py       # v6 ★ BEST: tuned GB/XGB, 14 features (78.5%)
├── submission.csv             # Best predictions (v6)
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
| v3      | 83.5%       | 77.0%     | Stacking (7 models + meta LR), 13 features, full 891 train |
| v4      | 81.7%       | 77.5%     | KNN imputation, Age×Pclass/Fare×Pclass, LR_CV |
| v5      | 82.8%       | 77.0%     | 23 features (ticket/cabin/deck), 8-model blend |
| **v6**  | **83.6%**   | **78.5%** | **Tuned GB/XGB (n=180, lr=0.04, subsample=0.75), 14 core features** |

## Usage

```bash
pip install -r requirements.txt

# v6 (best - 78.5% public LB)
python titanic_kaggle_v6.py

# v4 (77.5% - simplest approach)
python titanic_kaggle_v4.py

# v1 / v2 / v3 / v5 (alternative approaches)
python titanic_kaggle.py
```

## Author

**Koketso Raphasha** — [Kaggle](https://kaggle.com/Raphasha27) | [Portfolio](https://github.com/Raphasha27)
