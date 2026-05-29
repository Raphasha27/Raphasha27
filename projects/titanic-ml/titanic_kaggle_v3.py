"""
Titanic v3 - Generalization-focused, trained on all 891 rows
"""
import os, warnings, numpy as np, pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import KNNImputer
from sklearn.linear_model import LogisticRegression, RidgeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier, ExtraTreesClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score
from xgboost import XGBClassifier
from scipy.stats import mode

warnings.filterwarnings('ignore')
BASE = r"C:\Users\nelso\AppData\Local\Temp\opencode\titanic-run"
N_FOLDS = 10
SEED = 42

def engineer(df):
    data = df.copy()
    data['Title'] = data['Name'].str.extract(r' ([A-Za-z]+)\.', expand=False)
    data['Title'] = data['Title'].map({
        'Mr':'Mr','Miss':'Miss','Mrs':'Mrs','Master':'Master'
    }).fillna('Rare')
    data['FamilySize'] = data['SibSp'] + data['Parch'] + 1
    data['IsAlone'] = (data['FamilySize'] == 1).astype(int)
    data['HasCabin'] = data['Cabin'].notna().astype(int)
    data['Sex'] = (data['Sex'] == 'male').astype(int)
    data['Embarked'] = data['Embarked'].fillna('S').map({'S':0,'C':1,'Q':2}).fillna(0).astype(int)
    data['Age'] = data.groupby('Title')['Age'].transform(lambda x: x.fillna(x.median()))
    data['Age'] = data['Age'].fillna(data['Age'].median())
    data['Fare'] = data.groupby('Pclass')['Fare'].transform(lambda x: x.fillna(x.median()))
    data['Fare'] = data['Fare'].fillna(data['Fare'].median())
    return data

def make_features(data):
    df = data.copy()
    df = engineer(df)
    title_map = {'Mr':0,'Miss':1,'Mrs':2,'Master':3,'Rare':4}
    df['Title'] = df['Title'].map(title_map).fillna(4).astype(int)
    df['Pclass'] = df['Pclass'].astype(int)
    df['FareBin'] = pd.qcut(df['Fare'].rank(method='first'), 4, labels=False).astype(int)
    df['AgeBin'] = pd.cut(df['Age'], bins=[0,5,12,18,30,50,80], labels=False).fillna(0).astype(int)
    return df

# Load
train = pd.read_csv(os.path.join(BASE, 'train.csv'))
test = pd.read_csv(os.path.join(BASE, 'kaggle_test.csv'))

# Feature engineering on full dataset + test
full = pd.concat([train, test], keys=['train','test'], names=['src']).reset_index(level=1, drop=True)
full_feat = make_features(full)

X_full = full_feat.loc['train'].drop(columns=['Survived','Name','Ticket','Cabin','PassengerId'], errors='ignore')
y_full = train['Survived'].values
X_test = full_feat.loc['test'].drop(columns=['Survived','Name','Ticket','Cabin','PassengerId'], errors='ignore')
test_ids = test['PassengerId'].values

# Scale
scaler = StandardScaler()
X_full_s = scaler.fit_transform(X_full)
X_test_s = scaler.transform(X_test)

print(f'Features ({X_full.shape[1]}): {list(X_full.columns)}')
print(f'Train: {X_full.shape[0]} | Test: {X_test.shape[0]}')

cv = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)

# Models with strong regularization
models = {
    'LogisticRegression': LogisticRegression(C=0.3, max_iter=3000, solver='liblinear', random_state=SEED),
    'RidgeClassifier': RidgeClassifier(alpha=5.0, random_state=SEED),
    'RandomForest': RandomForestClassifier(n_estimators=300, max_depth=5, min_samples_leaf=8, random_state=SEED),
    'GradientBoosting': GradientBoostingClassifier(n_estimators=200, max_depth=3, learning_rate=0.03, subsample=0.7, random_state=SEED),
    'ExtraTrees': ExtraTreesClassifier(n_estimators=300, max_depth=5, min_samples_leaf=8, random_state=SEED),
    'XGBoost': XGBClassifier(n_estimators=300, max_depth=3, learning_rate=0.02, subsample=0.7,
                              colsample_bytree=0.7, reg_lambda=5.0, reg_alpha=3.0, eval_metric='logloss', random_state=SEED),
    'KNN': KNeighborsClassifier(n_neighbors=15, weights='distance', p=2),
}

print('\nCross-validation scores (10-fold):')
scores_dict = {}
for name, model in models.items():
    scores = cross_val_score(model, X_full_s, y_full, cv=cv, scoring='accuracy')
    scores_dict[name] = scores.mean()
    print(f'  {name:20s} | CV: {scores.mean():.4f} (+/- {scores.std()*2:.4f})')

# Build ensemble with weights from CV
top_models = sorted(scores_dict.items(), key=lambda x: x[1], reverse=True)
print(f'\nTop models: {[m[0] for m in top_models[:5]]}')

# Train all models on full data and generate OOF predictions for stacking
print('\nGenerating OOF predictions for stacking...')
oof_preds = np.zeros((X_full.shape[0], len(models)))
test_preds = np.zeros((X_test.shape[0], len(models)))

for i, (name, model) in enumerate(models.items()):
    oof = np.zeros(X_full.shape[0])
    test_fold_preds = np.zeros((X_test.shape[0], N_FOLDS))
    for fold, (tr_idx, val_idx) in enumerate(cv.split(X_full_s, y_full)):
        model.fit(X_full_s[tr_idx], y_full[tr_idx])
        oof[val_idx] = model.predict_proba(X_full_s[val_idx])[:, 1] if hasattr(model, 'predict_proba') else model.decision_function(X_full_s[val_idx])
        if hasattr(model, 'predict_proba'):
            test_fold_preds[:, fold] = model.predict_proba(X_test_s)[:, 1]
        else:
            test_fold_preds[:, fold] = model.decision_function(X_test_s)
    oof_preds[:, i] = oof
    test_preds[:, i] = test_fold_preds.mean(axis=1)
    print(f'  {name:20s} OOF done')

# Train meta-learner (LogisticRegression on OOF predictions)
meta_lr = LogisticRegression(C=1.0, max_iter=2000, solver='liblinear', random_state=SEED)
meta_lr.fit(oof_preds, y_full)
meta_cv_scores = cross_val_score(meta_lr, oof_preds, y_full, cv=cv, scoring='accuracy')
print(f'\n  Stacking (meta LR)           | CV: {meta_cv_scores.mean():.4f} (+/- {meta_cv_scores.std()*2:.4f})')

# Also try simple average ensemble
avg_probs = test_preds.mean(axis=1)
avg_preds = (avg_probs > 0.5).astype(int)

# Meta prediction
meta_probs = meta_lr.predict_proba(test_preds)[:, 1]
meta_preds = (meta_probs > 0.5).astype(int)

# Also train a final model on all data for comparison
final_rf = RandomForestClassifier(n_estimators=300, max_depth=5, min_samples_leaf=8, random_state=SEED)
final_rf.fit(X_full_s, y_full)
final_preds = final_rf.predict(X_test_s)

# Ensemble of ensembles
final_probs = (avg_probs + meta_probs + final_rf.predict_proba(X_test_s)[:, 1]) / 3
final_preds_ensemble = (final_probs > 0.5).astype(int)

# Distribution comparison
print('\nSubmission distributions:')
print(f'  Simple avg: {pd.Series(avg_preds).value_counts().to_dict()}')
print(f'  Meta LR:    {pd.Series(meta_preds).value_counts().to_dict()}')
print(f'  RF final:   {pd.Series(final_preds).value_counts().to_dict()}')
print(f'  Tri-avg:    {pd.Series(final_preds_ensemble).value_counts().to_dict()}')

# Pick the most balanced (closest to ~38% survival rate = ~159 survivors)
target = int(418 * 0.383)
choices = {'avg': avg_preds, 'meta': meta_preds, 'rf': final_preds, 'tri': final_preds_ensemble}
best_name = min(choices, key=lambda k: abs(choices[k].sum() - target))
best_preds = choices[best_name]
print(f'\nUsing: {best_name} ({best_preds.sum()} survived, target ~{target})')

sub = pd.DataFrame({'PassengerId': test_ids, 'Survived': best_preds})
sub_path = os.path.join(BASE, 'titanic_submission.csv')
sub.to_csv(sub_path, index=False)
print(f'\nSaved: {sub_path}')
print(f'Ready to submit: kaggle competitions submit -c titanic -f "{sub_path}" -m "v3"')
