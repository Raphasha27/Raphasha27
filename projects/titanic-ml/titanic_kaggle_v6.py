"""
Titanic v6 - Tuned GradientBoosting, feature selection from v4 best
Target: 78%+ public LB
"""
import os, warnings, numpy as np, pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.impute import KNNImputer
from sklearn.linear_model import LogisticRegressionCV
from sklearn.ensemble import GradientBoostingClassifier
from xgboost import XGBClassifier

warnings.filterwarnings('ignore')
BASE = r"C:\Users\nelso\AppData\Local\Temp\opencode\titanic-run"
SEED = 42

def make_features(df):
    data = df.copy()
    data['Title'] = data['Name'].str.extract(r' ([A-Za-z]+)\.', expand=False)
    data['Title'] = data['Title'].map({'Mr':'Mr','Miss':'Miss','Mrs':'Mrs','Master':'Master'}).fillna('Rare')
    title_map = {'Mr':0,'Miss':1,'Mrs':2,'Master':3,'Rare':4}
    data['Title'] = data['Title'].map(title_map).fillna(4).astype(int)
    data['FamilySize'] = data['SibSp'] + data['Parch'] + 1
    data['IsAlone'] = (data['FamilySize'] == 1).astype(int)
    data['HasCabin'] = data['Cabin'].notna().astype(int)
    data['Sex'] = (data['Sex'] == 'male').astype(int)
    data['Embarked'] = data['Embarked'].fillna('S').map({'S':0,'C':1,'Q':2}).fillna(0).astype(int)
    data['Pclass'] = data['Pclass'].astype(int)
    return data

train = pd.read_csv(os.path.join(BASE, 'train.csv'))
test = pd.read_csv(os.path.join(BASE, 'kaggle_test.csv'))

full = pd.concat([make_features(train), make_features(test)], ignore_index=True)
age_cols = ['Age','Pclass','Sex','Fare','SibSp','Parch','Title','FamilySize']
age_data = full[age_cols].copy()
knn = KNNImputer(n_neighbors=5)
full['Age'] = pd.DataFrame(knn.fit_transform(age_data), columns=age_cols)['Age']
fare_med = full.groupby('Pclass')['Fare'].transform('median')
full['Fare'] = full['Fare'].fillna(fare_med)

# V4 core features
full['Age_Pclass'] = full['Age'] * full['Pclass']
full['Fare_Pclass'] = full['Fare'] / (full['Pclass'] + 1)
full['FamilyCat'] = pd.cut(full['FamilySize'], bins=[0,1,4,20], labels=[0,1,2]).astype(int)

feature_cols = ['Pclass','Sex','Age','SibSp','Parch','Fare','Embarked','Title',
                'FamilySize','IsAlone','HasCabin','Age_Pclass','Fare_Pclass','FamilyCat']

X_full = full.iloc[:len(train)][feature_cols]
X_test = full.iloc[len(train):][feature_cols]
y_full = train['Survived'].values

scaler = StandardScaler()
X_full_s = scaler.fit_transform(X_full)
X_test_s = scaler.transform(X_test)

print(f'Features: {len(feature_cols)}')
cv = StratifiedKFold(n_splits=10, shuffle=True, random_state=SEED)

# Models
models = {
    'LR_CV': LogisticRegressionCV(Cs=[0.01,0.05,0.1,0.2,0.3,0.5,1.0], cv=5, max_iter=3000, solver='liblinear', random_state=SEED),
    'GB_low': GradientBoostingClassifier(n_estimators=100, max_depth=3, learning_rate=0.05, subsample=0.8, random_state=SEED),
    'GB_med': GradientBoostingClassifier(n_estimators=200, max_depth=3, learning_rate=0.03, subsample=0.7, random_state=SEED),
    'GB_high': GradientBoostingClassifier(n_estimators=300, max_depth=3, learning_rate=0.02, subsample=0.7, random_state=SEED),
    'XGB': XGBClassifier(n_estimators=300, max_depth=3, learning_rate=0.02, subsample=0.7,
                          colsample_bytree=0.7, reg_lambda=5.0, reg_alpha=3.0, eval_metric='logloss', random_state=SEED),
    'GB_tuned': GradientBoostingClassifier(n_estimators=180, max_depth=3, learning_rate=0.04, subsample=0.75,
                                            min_samples_leaf=5, min_samples_split=10, random_state=SEED),
}

print('\n10-fold CV:')
results = []
for name, model in models.items():
    scores = cross_val_score(model, X_full_s, y_full, cv=cv, scoring='accuracy')
    results.append((name, scores.mean(), model))
    print(f'  {name:10s} | CV: {scores.mean():.4f} (+/- {scores.std()*2:.4f})')

# Best model
results.sort(key=lambda x: x[1], reverse=True)
best_name, best_score, best_model = results[0]
print(f'\nBest: {best_name} ({best_score:.4f})')

# Blend top 2 models
top2 = results[:2]
test_probs = np.zeros((X_test.shape[0], len(top2)))
for i, (name, _, model) in enumerate(top2):
    model.fit(X_full_s, y_full)
    test_probs[:, i] = model.predict_proba(X_test_s)[:, 1]
blend_preds = (test_probs.mean(axis=1) > 0.5).astype(int)

# Solos
for name, score, model in results[:3]:
    model.fit(X_full_s, y_full)
    p = model.predict(X_test_s)
    print(f'  {name:10s} solo: {p.sum()} survived')

print(f'  Blend top2:  {blend_preds.sum()} survived')

target = int(418 * 0.383)
solo_preds = {}
for name, score, model in results[:3]:
    model.fit(X_full_s, y_full)
    solo_preds[name] = model.predict(X_test_s)
solo_preds['blend'] = blend_preds

best_key = min(solo_preds, key=lambda k: abs(solo_preds[k].sum() - target))
final_preds = solo_preds[best_key]
print(f'\nUsing: {best_key} ({final_preds.sum()} survived)')

sub = pd.DataFrame({'PassengerId': test['PassengerId'], 'Survived': final_preds})
sub.to_csv(os.path.join(BASE, 'titanic_submission.csv'), index=False)
print('Saved')
