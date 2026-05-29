"""
Titanic v4 - Robust generalization, KNN imputation, interaction features
Focus: narrow the val/LB gap by reducing overfitting
"""
import os, warnings, numpy as np, pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.impute import KNNImputer
from sklearn.linear_model import LogisticRegression, LogisticRegressionCV
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score
from xgboost import XGBClassifier

warnings.filterwarnings('ignore')
BASE = r"C:\Users\nelso\AppData\Local\Temp\opencode\titanic-run"
SEED = 42

def make_features(df):
    data = df.copy()
    data['Title'] = data['Name'].str.extract(r' ([A-Za-z]+)\.', expand=False)
    data['Title'] = data['Title'].map({
        'Mr':'Mr','Miss':'Miss','Mrs':'Mrs','Master':'Master'}).fillna('Rare')
    title_map = {'Mr':0,'Miss':1,'Mrs':2,'Master':3,'Rare':4}
    data['Title'] = data['Title'].map(title_map).fillna(4).astype(int)
    data['FamilySize'] = data['SibSp'] + data['Parch'] + 1
    data['IsAlone'] = (data['FamilySize'] == 1).astype(int)
    data['HasCabin'] = data['Cabin'].notna().astype(int)
    data['Sex'] = (data['Sex'] == 'male').astype(int)
    data['Embarked'] = data['Embarked'].fillna('S').map({'S':0,'C':1,'Q':2}).fillna(0).astype(int)
    data['Pclass'] = data['Pclass'].astype(int)
    # Robust features
    data['Age_Pclass'] = data['Age'].fillna(data['Age'].median()) * data['Pclass']
    data['Fare_Pclass'] = data['Fare'].fillna(data['Fare'].median()) / data['Pclass']
    data['FamilyCat'] = pd.cut(data['FamilySize'], bins=[0,1,4,20], labels=[0,1,2]).astype(int)
    data['SibSp'] = data['SibSp'].clip(0, 3)
    data['Parch'] = data['Parch'].clip(0, 3)
    return data

# Load
train = pd.read_csv(os.path.join(BASE, 'train.csv'))
test = pd.read_csv(os.path.join(BASE, 'kaggle_test.csv'))

# Combine for consistent feature engineering
full = pd.concat([train.drop('Survived', axis=1), test], ignore_index=True)
full_feat = make_features(full)

# KNN imputation for Age
age_idx = full_feat.columns.get_loc('Age') if 'Age' in full_feat.columns else -1
if age_idx >= 0:
    age_corr_cols = ['Age', 'Pclass', 'Sex', 'Fare', 'SibSp', 'Parch', 'Title', 'FamilySize']
    age_data = full_feat[age_corr_cols].copy()
    knn_imp = KNNImputer(n_neighbors=5)
    age_data_imp = pd.DataFrame(knn_imp.fit_transform(age_data), columns=age_corr_cols)
    full_feat['Age'] = age_data_imp['Age']

# Fare imputation by Pclass
fare_medians = full_feat.groupby('Pclass')['Fare'].transform('median')
full_feat['Fare'] = full_feat['Fare'].fillna(fare_medians)

X_full = full_feat.iloc[:len(train)]
X_test = full_feat.iloc[len(train):]
y_full = train['Survived'].values
test_ids = test['PassengerId'].values

feature_cols = ['Pclass','Sex','Age','SibSp','Parch','Fare','Embarked','Title',
                'FamilySize','IsAlone','HasCabin','Age_Pclass','Fare_Pclass','FamilyCat']
X_full = X_full[feature_cols]
X_test = X_test[feature_cols]

scaler = StandardScaler()
X_full_s = scaler.fit_transform(X_full)
X_test_s = scaler.transform(X_test)

print(f'Features ({len(feature_cols)}): {feature_cols}')

cv = StratifiedKFold(n_splits=10, shuffle=True, random_state=SEED)

models = {
    'LR_L1': LogisticRegression(C=0.2, penalty='l1', solver='liblinear', max_iter=3000, random_state=SEED),
    'LR_L2': LogisticRegression(C=0.3, penalty='l2', solver='liblinear', max_iter=3000, random_state=SEED),
    'LR_CV': LogisticRegressionCV(Cs=[0.01,0.05,0.1,0.2,0.3,0.5,1.0], cv=5, max_iter=3000, solver='liblinear', random_state=SEED),
    'RF': RandomForestClassifier(n_estimators=200, max_depth=4, min_samples_leaf=10, random_state=SEED),
    'GB': GradientBoostingClassifier(n_estimators=200, max_depth=3, learning_rate=0.03, subsample=0.7, random_state=SEED),
    'ET': ExtraTreesClassifier(n_estimators=200, max_depth=4, min_samples_leaf=10, random_state=SEED),
    'SVC': SVC(kernel='rbf', C=0.3, gamma='scale', probability=True, random_state=SEED),
    'XGB': XGBClassifier(n_estimators=200, max_depth=3, learning_rate=0.02, subsample=0.7,
                          colsample_bytree=0.7, reg_lambda=5.0, reg_alpha=3.0, eval_metric='logloss', random_state=SEED),
}

print('\nCross-validation (10-fold):')
for name, model in models.items():
    scores = cross_val_score(model, X_full_s, y_full, cv=cv, scoring='accuracy')
    print(f'  {name:8s} | CV: {scores.mean():.4f} (+/- {scores.std()*2:.4f})')

# Train final ensemble: simple average of top models' probabilities
top_names = ['LR_CV', 'GB', 'RF', 'ET', 'XGB']
print(f'\nEnsemble: {top_names} (avg probability)')

test_probs = np.zeros((X_test.shape[0], len(top_names)))
for i, name in enumerate(top_names):
    model = models[name]
    model.fit(X_full_s, y_full)
    test_probs[:, i] = model.predict_proba(X_test_s)[:, 1]

avg_probs = test_probs.mean(axis=1)
preds = (avg_probs > 0.5).astype(int)

# Also try individual best model
lr_cv = models['LR_CV']
lr_cv.fit(X_full_s, y_full)
lr_preds = lr_cv.predict(X_test_s)

# Choose: pick the one with survival count closest to expected ~38%
target = int(418 * 0.383)
for name, p in [('Ensemble', preds), ('LR_CV', lr_preds)]:
    print(f'  {name}: {p.sum()} survived (target ~{target})')

final_preds = preds if abs(preds.sum() - target) <= abs(lr_preds.sum() - target) else lr_preds
print(f'\nUsing: {"Ensemble" if final_preds is preds else "LR_CV"} ({final_preds.sum()} survived)')

sub = pd.DataFrame({'PassengerId': test_ids, 'Survived': final_preds})
sub_path = os.path.join(BASE, 'titanic_submission.csv')
sub.to_csv(sub_path, index=False)
print(f'Saved: {sub_path}')
