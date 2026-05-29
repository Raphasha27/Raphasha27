"""
Titanic v7 - Surname/ticket groups with leave-one-out encoding (no target leakage)
Target: 80%+ public LB
"""
import os, warnings, numpy as np, pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.impute import KNNImputer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from xgboost import XGBClassifier

warnings.filterwarnings('ignore')
BASE = r"C:\Users\nelso\AppData\Local\Temp\opencode\titanic-run"
SEED = 42

def base_features(df):
    data = df.copy()
    data['Title'] = data['Name'].str.extract(r' ([A-Za-z]+)\.', expand=False)
    data['Title'] = data['Title'].map({'Mr':'Mr','Miss':'Miss','Mrs':'Mrs','Master':'Master'}).fillna('Rare')
    data['Title'] = data['Title'].map({'Mr':0,'Miss':1,'Mrs':2,'Master':3,'Rare':4}).fillna(4).astype(int)
    data['FamilySize'] = data['SibSp'] + data['Parch'] + 1
    data['IsAlone'] = (data['FamilySize'] == 1).astype(int)
    data['HasCabin'] = data['Cabin'].notna().astype(int)
    data['Sex'] = (data['Sex'] == 'male').astype(int)
    data['Embarked'] = data['Embarked'].fillna('S').map({'S':0,'C':1,'Q':2}).fillna(0).astype(int)
    data['Pclass'] = data['Pclass'].astype(int)
    data['Surname'] = data['Name'].str.extract(r'^([A-Za-z]+)', expand=False)
    return data

train = pd.read_csv(os.path.join(BASE, 'train.csv'))
test = pd.read_csv(os.path.join(BASE, 'kaggle_test.csv'))
test_ids = test['PassengerId'].values

full = pd.concat([train.drop('Survived', axis=1), test], ignore_index=True)
full_bf = base_features(full)

# Leave-one-out family survival rate
train_bf = full_bf.iloc[:len(train)].copy()
train_bf['Survived'] = train['Survived'].values
grp = train_bf.groupby(['Surname', 'Ticket'])['Survived']
train_bf['FamilyCount'] = grp.transform('count')
train_bf['FamilySum'] = grp.transform('sum')
train_bf['FamilySurvivalRate'] = np.where(
    train_bf['FamilyCount'] > 1,
    (train_bf['FamilySum'] - train_bf['Survived']) / (train_bf['FamilyCount'] - 1),
    0.5
).clip(0, 1)

# Test set: use full training group mean
family_stats = train_bf.groupby(['Surname', 'Ticket']).agg(
    FamilySurvivalRate_lookup=('Survived', 'mean'),
    FamilyCount_lookup=('Survived', 'count')
).reset_index()

test_bf = full_bf.iloc[len(train):].merge(family_stats, on=['Surname', 'Ticket'], how='left')
test_bf['FamilySurvivalRate'] = test_bf['FamilySurvivalRate_lookup'].fillna(0.5)
test_bf['FamilyCount'] = test_bf['FamilyCount_lookup'].fillna(1).astype(int)

# Full feature set
train_features = train_bf[['Pclass','Sex','Age','SibSp','Parch','Fare','Embarked','Title',
    'FamilySize','IsAlone','HasCabin','FamilySurvivalRate','FamilyCount']].copy()
test_features = test_bf[['Pclass','Sex','Age','SibSp','Parch','Fare','Embarked','Title',
    'FamilySize','IsAlone','HasCabin','FamilySurvivalRate','FamilyCount']].copy()

# KNN imputation
full_feat = pd.concat([train_features, test_features], ignore_index=True)
age_cols = ['Age','Pclass','Sex','Fare','SibSp','Parch','Title','FamilySize']
age_data = full_feat[age_cols].copy()
knn = KNNImputer(n_neighbors=7)
full_feat['Age'] = pd.DataFrame(knn.fit_transform(age_data), columns=age_cols)['Age']
fare_med = full_feat.groupby('Pclass')['Fare'].transform('median')
full_feat['Fare'] = full_feat['Fare'].fillna(fare_med)

# Interactions
full_feat['Age_Pclass'] = full_feat['Age'] * full_feat['Pclass']
full_feat['Fare_Pclass'] = full_feat['Fare'] / (full_feat['Pclass'] + 1)
full_feat['FamSurv_Age'] = full_feat['FamilySurvivalRate'] * full_feat['Age'] / 10

feature_cols = ['Pclass','Sex','Age','SibSp','Parch','Fare','Embarked','Title',
    'FamilySize','IsAlone','HasCabin','FamilySurvivalRate','FamilyCount',
    'Age_Pclass','Fare_Pclass','FamSurv_Age']

X_full = full_feat.iloc[:len(train)][feature_cols]
X_test = full_feat.iloc[len(train):][feature_cols]
y_full = train['Survived'].values

scaler = StandardScaler()
X_full_s = scaler.fit_transform(X_full)
X_test_s = scaler.transform(X_test)

print(f'Features: {len(feature_cols)} | No target leakage (leave-one-out encoding)')

cv = StratifiedKFold(n_splits=10, shuffle=True, random_state=SEED)

models = {
    'GB': GradientBoostingClassifier(n_estimators=200, max_depth=3, learning_rate=0.035,
                                      subsample=0.75, min_samples_leaf=4, random_state=SEED),
    'XGB': XGBClassifier(n_estimators=400, max_depth=3, learning_rate=0.02, subsample=0.75,
                          colsample_bytree=0.75, reg_lambda=3.0, reg_alpha=2.0, eval_metric='logloss', random_state=SEED),
    'RF': RandomForestClassifier(n_estimators=500, max_depth=5, min_samples_leaf=6, random_state=SEED),
}

print('\n10-fold CV:')
for name, model in models.items():
    scores = cross_val_score(model, X_full_s, y_full, cv=cv, scoring='accuracy')
    print(f'  {name:5s} | CV: {scores.mean():.4f} (+/- {scores.std()*2:.4f})')

# Weighted blend
test_probs = np.zeros((X_test.shape[0], len(models)))
for i, (name, model) in enumerate(models.items()):
    model.fit(X_full_s, y_full)
    test_probs[:, i] = model.predict_proba(X_test_s)[:, 1]
blend_preds = (test_probs.mean(axis=1) > 0.5).astype(int)

target = int(418 * 0.383)
print(f'\nBlend: {blend_preds.sum()} survived (target ~{target})')

sub = pd.DataFrame({'PassengerId': test_ids, 'Survived': blend_preds})
sub_path = os.path.join(BASE, 'titanic_submission.csv')
sub.to_csv(sub_path, index=False)
print(f'Saved: {sub_path}')
