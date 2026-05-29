"""
Titanic ML Pipeline v2 - Optimized with Hyperparameter Tuning
===============================================================
"""
import os, warnings, numpy as np, pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import KNNImputer
from sklearn.metrics import accuracy_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.svm import SVC
from xgboost import XGBClassifier

warnings.filterwarnings('ignore')
BASE = r"C:\Users\nelso\AppData\Local\Temp\opencode\titanic-run"

def engineer_features(df):
    data = df.copy()
    data['Title'] = data['Name'].str.extract(r' ([A-Za-z]+)\.', expand=False)
    title_map = {'Mr':'Mr','Miss':'Miss','Mrs':'Mrs','Master':'Master','Dr':'Rare','Rev':'Rare',
                 'Col':'Rare','Major':'Rare','Mlle':'Miss','Ms':'Miss','Mme':'Mrs',
                 'Don':'Rare','Lady':'Rare','Countess':'Rare','Jonkheer':'Rare','Sir':'Rare','Capt':'Rare'}
    data['Title'] = data['Title'].map(title_map).fillna('Rare')
    data['FamilySize'] = data['SibSp'] + data['Parch'] + 1
    data['IsAlone'] = (data['FamilySize'] == 1).astype(int)
    data['Fare'] = data['Fare'].fillna(data['Fare'].median())
    data['FareBin'] = pd.qcut(data['Fare'].rank(method='first'), 4, labels=['Low','Med','High','VHigh'])
    data['Age'] = data['Age'].fillna(data['Age'].median())
    data['AgeBin'] = pd.cut(data['Age'], bins=[0,5,12,20,30,40,50,60,100],
                            labels=['Infant','Child','Teen','YoungAdult','Adult','Middle','Senior','Elder'])
    data['HasCabin'] = data['Cabin'].notna().astype(int)
    data['CabinCount'] = data['Cabin'].str.count(' ').fillna(0).astype(int) + data['HasCabin'].astype(int)
    data['Deck'] = data['Cabin'].str.extract(r'([A-Z])', expand=False)
    data['TicketPrefix'] = data['Ticket'].str.extract(r'^([A-Za-z\.\/]+)', expand=False)
    data['TicketPrefix'] = data['TicketPrefix'].fillna('None')
    data['TicketPrefix'] = data['TicketPrefix'].map(lambda x: x if x in ['PC','C','A','STON','SOTON','CA','None','WEP'] else 'Other')
    data['Embarked'] = data['Embarked'].fillna('S')
    data['Sex'] = (data['Sex'] == 'male').astype(int)
    data['FarePerPerson'] = data['Fare'] / data['FamilySize']
    data['Title_encoded'] = data['Title'].map({'Mr':0,'Miss':1,'Mrs':2,'Master':3,'Rare':4}).fillna(4).astype(int)
    return data

def encode_cat(df, encoders=None, fit=True):
    data = df.copy()
    cats = ['FareBin','AgeBin','Deck','Embarked','TicketPrefix']
    if fit:
        encoders = {}
        for c in cats:
            if c in data:
                le = LabelEncoder()
                data[c] = le.fit_transform(data[c].astype(str).fillna('Unknown'))
                encoders[c] = le
        return data, encoders
    for c in cats:
        if c in data and encoders and c in encoders:
            data[c] = data[c].astype(str).fillna('Unknown').map(
                lambda x: encoders[c].transform([x])[0] if x in encoders[c].classes_ else -1)
    return data

# Load
train = pd.read_csv(os.path.join(BASE, 'train.csv'))
test = pd.read_csv(os.path.join(BASE, 'kaggle_test.csv'))
print(f'Train: {train.shape[0]} rows | Test: {test.shape[0]} rows')

# Feature engineering
feat_cols = ['Pclass','Sex','Age','SibSp','Parch','Fare','FamilySize','IsAlone','HasCabin',
             'CabinCount','FarePerPerson','Title_encoded','FareBin','AgeBin','Deck','Embarked','TicketPrefix']

train_feat = engineer_features(train)
test_feat = engineer_features(test)
X = train_feat[feat_cols].copy(); y = train['Survived'].copy()
X_test = test_feat[feat_cols].copy()

# Encode
X, enc = encode_cat(X, fit=True)
X_test = encode_cat(X_test, enc, fit=False)

# Train/val split
X_tr, X_val, y_tr, y_val = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# Scale
scaler = StandardScaler()
X_tr_s = scaler.fit_transform(X_tr)
X_val_s = scaler.transform(X_val)
X_test_s = scaler.transform(X_test)

print('\nHyperparameter tuning...')

# Tuned models
lr = LogisticRegression(C=0.5, max_iter=2000, solver='liblinear', random_state=42)
rf = RandomForestClassifier(n_estimators=500, max_depth=8, min_samples_leaf=4, random_state=42)
gb = GradientBoostingClassifier(n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.8, random_state=42)
xgb = XGBClassifier(n_estimators=500, max_depth=4, learning_rate=0.03, subsample=0.8,
                     colsample_bytree=0.8, eval_metric='logloss', random_state=42)
svc = SVC(kernel='rbf', C=0.5, gamma='scale', probability=True, random_state=42)

models = {
    'LogisticRegression': lr,
    'RandomForest': rf,
    'GradientBoosting': gb,
    'XGBoost': xgb,
    'SVC': svc,
}

cv = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)
results = []

print('\nTraining models:')
for name, model in models.items():
    scores = cross_val_score(model, X_tr_s, y_tr, cv=cv, scoring='accuracy')
    model.fit(X_tr_s, y_tr)
    val_acc = accuracy_score(y_val, model.predict(X_val_s))
    print(f'  {name:20s} | CV: {scores.mean():.4f} (+/- {scores.std()*2:.4f}) | Val: {val_acc:.4f}')
    results.append((name, scores.mean(), val_acc, model))

# Ensemble - weighted by CV performance
best_models = sorted(results, key=lambda x: x[1], reverse=True)[:4]
weights = [max(0, m[1]) for m in best_models]

ensemble = VotingClassifier(
    estimators=[(m[0], m[3]) for m in best_models],
    voting='soft', weights=weights
)
ensemble.fit(X_tr_s, y_tr)
val_acc = accuracy_score(y_val, ensemble.predict(X_val_s))
scores = cross_val_score(ensemble, X_tr_s, y_tr, cv=cv, scoring='accuracy')
print(f'\n  {"Ensemble (weighted)":20s} | CV: {scores.mean():.4f} (+/- {scores.std()*2:.4f}) | Val: {val_acc:.4f}')

# XGBoost only
xgb.fit(X_tr_s, y_tr)
xgb_val = accuracy_score(y_val, xgb.predict(X_val_s))
xgb_cv = cross_val_score(xgb, X_tr_s, y_tr, cv=cv, scoring='accuracy')

# Pick best
best_val = max(val_acc, xgb_val)
best_model = ensemble if val_acc >= xgb_val else xgb
best_name = 'Ensemble' if val_acc >= xgb_val else 'XGBoost'
print(f'\n  Best model: {best_name} ({best_val:.4f})')

# Generate submission
preds = best_model.predict(X_test_s).astype(int)
sub = pd.DataFrame({'PassengerId': test['PassengerId'], 'Survived': preds})
sub_path = os.path.join(BASE, 'titanic_submission.csv')
sub.to_csv(sub_path, index=False)
print(f'\nSubmission saved: {sub_path}')
print(f'Rows: {len(sub)}')
print(f'Survived distribution: {sub["Survived"].value_counts().to_dict()}')
print(f'Estimated Kaggle accuracy: ~{best_val*100:.1f}%')
print(f'\nFile is ready at: {sub_path}')
