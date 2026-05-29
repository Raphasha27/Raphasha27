"""
Titanic v5 - Ticket/cabin features, feature selection, blended ensemble
Target: 78%+ Kaggle public LB
"""
import os, warnings, numpy as np, pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_score, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.impute import KNNImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier, AdaBoostClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score
from xgboost import XGBClassifier

warnings.filterwarnings('ignore')
BASE = r"C:\Users\nelso\AppData\Local\Temp\opencode\titanic-run"
SEED = 42

def make_features(df):
    data = df.copy()
    # Title
    data['Title'] = data['Name'].str.extract(r' ([A-Za-z]+)\.', expand=False)
    data['Title'] = data['Title'].map({'Mr':'Mr','Miss':'Miss','Mrs':'Mrs','Master':'Master'}).fillna('Rare')
    title_map = {'Mr':0,'Miss':1,'Mrs':2,'Master':3,'Rare':4}
    data['Title'] = data['Title'].map(title_map).fillna(4).astype(int)
    # Family
    data['FamilySize'] = data['SibSp'] + data['Parch'] + 1
    data['IsAlone'] = (data['FamilySize'] == 1).astype(int)
    data['IsSmallFamily'] = ((data['FamilySize'] >= 2) & (data['FamilySize'] <= 4)).astype(int)
    # Cabin
    data['HasCabin'] = data['Cabin'].notna().astype(int)
    data['Deck'] = data['Cabin'].str.extract(r'([A-Z])', expand=False)
    data['Deck'] = data['Deck'].map({'A':0,'B':1,'C':2,'D':3,'E':4,'F':5,'G':6,'T':7}).fillna(-1).astype(int)
    data['CabinCount'] = data['Cabin'].str.count(' ').fillna(0).astype(int) + data['HasCabin'].astype(int)
    # Ticket
    data['TicketPrefix'] = data['Ticket'].str.extract(r'^([A-Za-z\.\/]+)', expand=False).fillna('None')
    common_prefixes = ['PC','C','A','STON','SOTON','CA','WEP','SC','SOC','LINE','S.O.C']
    data['TicketPrefix'] = data['TicketPrefix'].apply(lambda x: x if x in common_prefixes else 'Other')
    ticket_prefix_map = {p:i for i,p in enumerate(['None','Other','PC','C','A','STON','SOTON','CA','WEP','SC','SOC','LINE','S.O.C'])}
    data['TicketPrefix'] = data['TicketPrefix'].map(ticket_prefix_map).fillna(0).astype(int)
    # Ticket group size (same ticket = same group)
    ticket_groups = data.groupby('Ticket')['PassengerId'].transform('count')
    data['TicketGroupSize'] = ticket_groups
    data['IsLargeTicketGroup'] = (ticket_groups > 3).astype(int)
    # Sex
    data['Sex'] = (data['Sex'] == 'male').astype(int)
    # Embarked
    data['Embarked'] = data['Embarked'].fillna('S').map({'S':0,'C':1,'Q':2}).fillna(0).astype(int)
    # Pclass
    data['Pclass'] = data['Pclass'].astype(int)
    # Age imputation (KNN)
    age_cols = ['Age','Pclass','Sex','Fare','SibSp','Parch','Title','FamilySize']
    age_data = data[age_cols].copy()
    knn = KNNImputer(n_neighbors=5)
    data['Age'] = pd.DataFrame(knn.fit_transform(age_data), columns=age_cols)['Age']
    # Fare imputation
    fare_med = data.groupby('Pclass')['Fare'].transform('median')
    data['Fare'] = data['Fare'].fillna(fare_med)
    # Interactions
    data['Age_Pclass'] = data['Age'] * data['Pclass']
    data['Fare_Pclass'] = data['Fare'] / (data['Pclass'] + 1)
    data['Age_Fare'] = data['Age'] * data['Fare'] / 100
    data['Family_Fare'] = data['Fare'] / data['FamilySize'].clip(1, 20)
    # Bins
    data['AgeBin'] = pd.cut(data['Age'], bins=[0,5,12,18,25,35,50,65,100], labels=range(8)).astype(int)
    data['FareBin'] = pd.qcut(data['Fare'].rank(method='first'), 5, labels=range(5)).astype(int)
    return data

train = pd.read_csv(os.path.join(BASE, 'train.csv'))
test = pd.read_csv(os.path.join(BASE, 'kaggle_test.csv'))
test_ids = test['PassengerId'].values

full = pd.concat([train.drop('Survived', axis=1), test], ignore_index=True)
full_feat = make_features(full)

X_full = full_feat.iloc[:len(train)]
X_test = full_feat.iloc[len(train):]
y_full = train['Survived'].values

feature_cols = ['Pclass','Sex','Age','SibSp','Parch','Fare','Embarked','Title',
                'FamilySize','IsAlone','IsSmallFamily','HasCabin','Deck','CabinCount',
                'TicketPrefix','TicketGroupSize','IsLargeTicketGroup',
                'Age_Pclass','Fare_Pclass','Age_Fare','Family_Fare','AgeBin','FareBin']

X_full = X_full[feature_cols]
X_test = X_test[feature_cols]

scaler = StandardScaler()
X_full_s = scaler.fit_transform(X_full)
X_test_s = scaler.transform(X_test)

print(f'Features: {len(feature_cols)}')
cv = StratifiedKFold(n_splits=10, shuffle=True, random_state=SEED)

# Diverse models
models = {
    'LR': LogisticRegression(C=0.2, max_iter=3000, solver='liblinear', random_state=SEED),
    'RF': RandomForestClassifier(n_estimators=300, max_depth=5, min_samples_leaf=8, random_state=SEED),
    'GB': GradientBoostingClassifier(n_estimators=300, max_depth=3, learning_rate=0.03, subsample=0.7, random_state=SEED),
    'ET': ExtraTreesClassifier(n_estimators=300, max_depth=5, min_samples_leaf=8, random_state=SEED),
    'SVC': SVC(kernel='rbf', C=0.3, gamma='scale', probability=True, random_state=SEED),
    'XGB': XGBClassifier(n_estimators=300, max_depth=3, learning_rate=0.02, subsample=0.7,
                          colsample_bytree=0.7, reg_lambda=5.0, reg_alpha=3.0, eval_metric='logloss', random_state=SEED),
    'KNN': KNeighborsClassifier(n_neighbors=15, weights='distance'),
    'ADA': AdaBoostClassifier(n_estimators=200, learning_rate=0.5, random_state=SEED),
}

print('\n10-fold CV:')
results = []
for name, model in models.items():
    scores = cross_val_score(model, X_full_s, y_full, cv=cv, scoring='accuracy')
    results.append((name, scores.mean(), scores.std()*2, model))
    print(f'  {name:5s} | CV: {scores.mean():.4f} (+/- {scores.std()*2:.4f})')

# Rank by CV
results.sort(key=lambda x: x[1], reverse=True)
print(f'\nRanking: {[r[0] for r in results]}')

# Build 3 different ensembles
# Ensemble A: top 4 by CV
top4 = results[:4]
probs_a = np.zeros((X_test.shape[0], len(top4)))
for i, (name, _, _, model) in enumerate(top4):
    model.fit(X_full_s, y_full)
    probs_a[:, i] = model.predict_proba(X_test_s)[:, 1]
preds_a = (probs_a.mean(axis=1) > 0.5).astype(int)

# Ensemble B: all models
probs_b = np.zeros((X_test.shape[0], len(results)))
for i, (name, _, _, model) in enumerate(results):
    model.fit(X_full_s, y_full)
    probs_b[:, i] = model.predict_proba(X_test_s)[:, 1]
preds_b = (probs_b.mean(axis=1) > 0.5).astype(int)

# Ensemble C: weighted by CV score
weights = np.array([max(r[1], 0.5) for r in results])
w_probs = np.average(probs_b, axis=1, weights=weights)
preds_c = (w_probs > 0.5).astype(int)

# Ensemble D: GB only (often strong solo)
best_solo = results[0][3]
best_solo.fit(X_full_s, y_full)
preds_d = best_solo.predict(X_test_s)

target = int(418 * 0.383)
for name, p in [('Top4 avg', preds_a), ('All avg', preds_b), ('Weighted', preds_c), (f'{results[0][0]} solo', preds_d)]:
    print(f'  {name:15s}: {p.sum()} survived (target ~{target})')

# Select closest to target
all_preds = {'A_top4': preds_a, 'B_all': preds_b, 'C_weighted': preds_c, 'D_solo': preds_d}
best_key = min(all_preds, key=lambda k: abs(all_preds[k].sum() - target))
final_preds = all_preds[best_key]
print(f'\nUsing: {best_key} ({final_preds.sum()} survived)')

sub = pd.DataFrame({'PassengerId': test_ids, 'Survived': final_preds})
sub_path = os.path.join(BASE, 'titanic_submission.csv')
sub.to_csv(sub_path, index=False)
print(f'Saved: {sub_path}')
