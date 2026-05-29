"""
Titanic: Machine Learning from Disaster
=========================================
Kaggle Competition Notebook
Author: Koketso Raphasha | Kaggle: Raphasha27

Pipeline:
  1. Load & inspect data
  2. Exploratory Data Analysis
  3. Feature Engineering
  4. Model Training & Comparison
  5. Ensemble Stacking
  6. Submission Generation
"""

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import (
    train_test_split, StratifiedKFold, cross_val_score
)
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import (
    RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
)
from sklearn.svm import SVC
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")
sns.set_style("darkgrid")
plt.rcParams["figure.figsize"] = (12, 6)

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =============================================================================
# 1. LOAD DATA
# =============================================================================
print("=" * 60)
print("1. LOADING DATA")
print("=" * 60)

train = pd.read_csv("../input/titanic/train.csv")
test = pd.read_csv("../input/titanic/test.csv")
sample_sub = pd.read_csv("../input/titanic/gender_submission.csv")

print(f"Train: {train.shape[0]} rows x {train.shape[1]} cols")
print(f"Test:  {test.shape[0]} rows x {test.shape[1]} cols")
print(f"\nTrain columns:\n{train.dtypes.to_string()}")
print(f"\nMissing values:\n{train.isnull().sum().to_string()}")

# =============================================================================
# 2. EXPLORATORY DATA ANALYSIS
# =============================================================================
print("\n" + "=" * 60)
print("2. EXPLORATORY DATA ANALYSIS")
print("=" * 60)

fig, axes = plt.subplots(2, 3, figsize=(15, 10))

sns.countplot(data=train, x="Survived", ax=axes[0, 0])
axes[0, 0].set_title("Survival Distribution (0=Died, 1=Survived)")

sns.countplot(data=train, x="Sex", hue="Survived", ax=axes[0, 1])
axes[0, 1].set_title("Survival by Sex")

sns.histplot(data=train, x="Age", hue="Survived", kde=True, bins=30, ax=axes[0, 2])
axes[0, 2].set_title("Age Distribution by Survival")

sns.countplot(data=train, x="Pclass", hue="Survived", ax=axes[1, 0])
axes[1, 0].set_title("Survival by Passenger Class")

sns.countplot(data=train, x="Embarked", hue="Survived", ax=axes[1, 1])
axes[1, 1].set_title("Survival by Embarkation Port")

sns.boxplot(data=train, x="Survived", y="Fare", ax=axes[1, 2])
axes[1, 2].set_title("Fare Distribution by Survival")

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "eda_overview.png"), dpi=100)

corr = train.select_dtypes(include=[np.number]).corr()
plt.figure(figsize=(10, 6))
sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f", linewidths=0.5)
plt.title("Feature Correlation Matrix")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "correlation_matrix.png"), dpi=100)

print("EDA charts saved to output/")

# =============================================================================
# 3. FEATURE ENGINEERING
# =============================================================================
print("\n" + "=" * 60)
print("3. FEATURE ENGINEERING")
print("=" * 60)

def engineer_features(df):
    data = df.copy()

    data["Title"] = data["Name"].str.extract(r" ([A-Za-z]+)\.", expand=False)
    title_mapping = {
        "Mr": "Mr", "Miss": "Miss", "Mrs": "Mrs", "Master": "Master",
        "Dr": "Rare", "Rev": "Rare", "Col": "Rare", "Major": "Rare",
        "Mlle": "Miss", "Ms": "Miss", "Mme": "Mrs",
        "Don": "Rare", "Lady": "Rare", "Countess": "Rare",
        "Jonkheer": "Rare", "Sir": "Rare", "Capt": "Rare"
    }
    data["Title"] = data["Title"].map(title_mapping).fillna("Rare")

    data["FamilySize"] = data["SibSp"] + data["Parch"] + 1
    data["IsAlone"] = (data["FamilySize"] == 1).astype(int)

    data["FareBin"] = pd.qcut(data["Fare"].fillna(data["Fare"].median()), 4,
                              labels=["Low", "Medium", "High", "VeryHigh"])

    data["AgeBin"] = pd.cut(data["Age"].fillna(data["Age"].median()),
                            bins=[0, 12, 20, 40, 60, 100],
                            labels=["Child", "Teen", "Adult", "MiddleAge", "Senior"])

    data["HasCabin"] = data["Cabin"].notna().astype(int)
    data["Deck"] = data["Cabin"].str.extract(r"([A-Z])", expand=False)

    data["Embarked"] = data["Embarked"].fillna("S")

    data["Sex"] = (data["Sex"] == "male").astype(int)

    return data


def encode_categorical(df, encoders=None, fit=True):
    data = df.copy()
    cat_cols = ["Title", "FareBin", "AgeBin", "Deck", "Embarked"]

    if fit:
        encoders = {}
        for col in cat_cols:
            if col in data.columns:
                le = LabelEncoder()
                data[col] = le.fit_transform(data[col].astype(str).fillna("Unknown"))
                encoders[col] = le
        return data, encoders
    else:
        for col in cat_cols:
            if col in data.columns and encoders and col in encoders:
                data[col] = data[col].astype(str).fillna("Unknown")
                data[col] = data[col].map(
                    lambda x: encoders[col].transform([x])[0]
                    if x in encoders[col].classes_ else -1
                )
        return data


train_feat = engineer_features(train)
test_feat = engineer_features(test)

feature_cols = [
    "Pclass", "Sex", "Age", "SibSp", "Parch", "Fare",
    "FamilySize", "IsAlone", "HasCabin",
    "Title", "FareBin", "AgeBin", "Deck", "Embarked"
]

X = train_feat[feature_cols].copy()
y = train["Survived"].copy()
X_test = test_feat[feature_cols].copy()
passenger_ids = test["PassengerId"]

# Impute missing values
imputer_num = SimpleImputer(strategy="median")
num_cols = ["Age", "Fare"]
X[num_cols] = imputer_num.fit_transform(X[num_cols])
X_test[num_cols] = imputer_num.transform(X_test[num_cols])

# Encode categorical features
X, encoders = encode_categorical(X, fit=True)
X_test = encode_categorical(X_test, encoders=encoders, fit=False)

print(f"Features after engineering: {list(X.columns)}")
print(f"Train shape: {X.shape} | Test shape: {X_test.shape}")

# =============================================================================
# 4. MODEL TRAINING & EVALUATION
# =============================================================================
print("\n" + "=" * 60)
print("4. MODEL TRAINING & CROSS-VALIDATION")
print("=" * 60)

X_train, X_val, y_train, y_val = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled = scaler.transform(X_val)
X_test_scaled = scaler.transform(X_test)

models = {
    "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
    "Random Forest": RandomForestClassifier(
        n_estimators=200, max_depth=10, random_state=42
    ),
    "Gradient Boosting": GradientBoostingClassifier(
        n_estimators=200, max_depth=5, random_state=42
    ),
    "XGBoost": XGBClassifier(
        n_estimators=200, max_depth=5, learning_rate=0.05,
        eval_metric="logloss", random_state=42
    ),
    "SVC": SVC(kernel="rbf", C=1.0, probability=True, random_state=42),
}

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
results = []

for name, model in models.items():
    scores = cross_val_score(model, X_train_scaled, y_train, cv=cv, scoring="accuracy")
    model.fit(X_train_scaled, y_train)
    val_pred = model.predict(X_val_scaled)
    val_acc = accuracy_score(y_val, val_pred)

    results.append({
        "Model": name,
        "CV Mean": f"{scores.mean():.4f} (+/- {scores.std() * 2:.4f})",
        "Validation Acc": f"{val_acc:.4f}",
    })
    print(f"\n  {name:25s} | CV: {scores.mean():.4f} | Val: {val_acc:.4f}")

results_df = pd.DataFrame(results)
print(f"\n{results_df.to_string(index=False)}")

# =============================================================================
# 5. ENSEMBLE STACKING
# =============================================================================
print("\n" + "=" * 60)
print("5. ENSEMBLE MODEL")
print("=" * 60)

ensemble = VotingClassifier(
    estimators=[
        ("rf", models["Random Forest"]),
        ("gb", models["Gradient Boosting"]),
        ("xgb", models["XGBoost"]),
        ("lr", models["Logistic Regression"]),
    ],
    voting="soft",
    weights=[2, 2, 2, 1],
)

ensemble.fit(X_train_scaled, y_train)
ensemble_val_acc = accuracy_score(y_val, ensemble.predict(X_val_scaled))
print(f"Ensemble Validation Accuracy: {ensemble_val_acc:.4f}")

scores = cross_val_score(ensemble, X_train_scaled, y_train, cv=cv, scoring="accuracy")
print(f"Ensemble CV Accuracy: {scores.mean():.4f} (+/- {scores.std() * 2:.4f})")

# Feature importance from Random Forest
rf_model = models["Random Forest"]
importances = pd.DataFrame({
    "Feature": X.columns,
    "Importance": rf_model.feature_importances_
}).sort_values("Importance", ascending=False)

plt.figure(figsize=(10, 6))
sns.barplot(data=importances.head(15), x="Importance", y="Feature")
plt.title("Top 15 Feature Importances (Random Forest)")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "feature_importance.png"), dpi=100)
print("\nTop 10 features:")
print(importances.head(10).to_string(index=False))

# =============================================================================
# 6. GENERATE SUBMISSION
# =============================================================================
print("\n" + "=" * 60)
print("6. GENERATING SUBMISSION")
print("=" * 60)

test_preds = ensemble.predict(X_test_scaled)
submission = pd.DataFrame({
    "PassengerId": passenger_ids,
    "Survived": test_preds.astype(int),
})
submission_path = os.path.join(OUTPUT_DIR, "submission.csv")
submission.to_csv(submission_path, index=False)
print(f"Submission saved to {submission_path}")
print(f"Predictions distribution:\n{submission['Survived'].value_counts().to_string()}")

print("\n" + "=" * 60)
print("DONE — READY FOR KAGGLE SUBMISSION")
print("=" * 60)
