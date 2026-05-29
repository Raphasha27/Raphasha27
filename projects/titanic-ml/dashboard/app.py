"""
Titanic Survival Predictor — Streamlit Dashboard
==================================================
Interactive web app for the Titanic ML model.
Predicts survival probability, shows feature importance, model comparison & EDA.

Usage:
    streamlit run app.py
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, roc_auc_score, roc_curve, confusion_matrix
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.svm import SVC

sns.set_style("darkgrid")
st.set_page_config(
    page_title="Titanic Survival Predictor",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def load_data():
    """Load Titanic dataset from URL or local cache."""
    train_url = "https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv"
    df = pd.read_csv(train_url)
    return df


@st.cache_resource
def train_models(df):
    """Train all models and return them along with processed data."""

    def engineer_features(data):
        d = data.copy()
        d["Title"] = d["Name"].str.extract(r" ([A-Za-z]+)\.", expand=False)
        title_map = {
            "Mr": "Mr", "Miss": "Miss", "Mrs": "Mrs", "Master": "Master",
            "Dr": "Rare", "Rev": "Rare", "Col": "Rare", "Major": "Rare",
            "Mlle": "Miss", "Ms": "Miss", "Mme": "Mrs",
            "Don": "Rare", "Lady": "Rare", "Countess": "Rare",
            "Jonkheer": "Rare", "Sir": "Rare", "Capt": "Rare",
        }
        d["Title"] = d["Title"].map(title_map).fillna("Rare")
        d["FamilySize"] = d["SibSp"] + d["Parch"] + 1
        d["IsAlone"] = (d["FamilySize"] == 1).astype(int)
        d["FareBin"] = pd.qcut(d["Fare"].fillna(d["Fare"].median()), 4,
                               labels=["Low", "Med", "High", "VHigh"])
        d["AgeBin"] = pd.cut(d["Age"].fillna(d["Age"].median()),
                             bins=[0, 12, 20, 40, 60, 100],
                             labels=["Child", "Teen", "Adult", "Middle", "Senior"])
        d["HasCabin"] = d["Cabin"].notna().astype(int)
        d["Deck"] = d["Cabin"].str.extract(r"([A-Z])", expand=False)
        d["Embarked"] = d["Embarked"].fillna("S")
        d["Sex"] = (d["Sex"] == "male").astype(int)
        return d

    feat_cols = ["Pclass", "Sex", "Age", "SibSp", "Parch", "Fare",
                 "FamilySize", "IsAlone", "HasCabin",
                 "Title", "FareBin", "AgeBin", "Deck", "Embarked"]

    df_feat = engineer_features(df)
    X = df_feat[feat_cols].copy()
    y = df["Survived"].copy()

    imptr = SimpleImputer(strategy="median")
    X[["Age", "Fare"]] = imptr.fit_transform(X[["Age", "Fare"]])

    cat_cols = ["Title", "FareBin", "AgeBin", "Deck", "Embarked"]
    encoders = {}
    for col in cat_cols:
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col].astype(str).fillna("Unknown"))
        encoders[col] = le

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)

    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=200, max_depth=5, random_state=42),
        "SVC": SVC(kernel="rbf", C=1.0, probability=True, random_state=42),
    }

    trained = {}
    results = []
    for name, model in models.items():
        model.fit(X_train_s, y_train)
        pred = model.predict(X_val_s)
        proba = model.predict_proba(X_val_s)[:, 1]
        acc = accuracy_score(y_val, pred)
        auc = roc_auc_score(y_val, proba)
        trained[name] = model
        results.append({"Model": name, "Accuracy": f"{acc:.4f}", "ROC AUC": f"{auc:.4f}"})

    ensemble = VotingClassifier(
        estimators=[("rf", trained["Random Forest"]),
                    ("gb", trained["Gradient Boosting"]),
                    ("lr", trained["Logistic Regression"])],
        voting="soft", weights=[2, 2, 1]
    )
    ensemble.fit(X_train_s, y_train)
    trained["Ensemble"] = ensemble
    pred_e = ensemble.predict(X_val_s)
    proba_e = ensemble.predict_proba(X_val_s)[:, 1]
    results.append({"Model": "Ensemble", "Accuracy": f"{accuracy_score(y_val, pred_e):.4f}",
                    "ROC AUC": f"{roc_auc_score(y_val, proba_e):.4f}"})

    return trained, scaler, encoders, imptr, X.columns.tolist(), pd.DataFrame(results), X_val_s, y_val


def predict_survival(model, scaler, encoders, imptr, features, input_data):
    """Predict survival probability for a single passenger."""
    df = pd.DataFrame([input_data])
    df["Title"] = "Mr" if input_data["Sex"] == "male" else "Mrs"
    df["FamilySize"] = input_data["SibSp"] + input_data["Parch"] + 1
    df["IsAlone"] = 1 if df["FamilySize"].values[0] == 1 else 0
    df["FareBin"] = "Med"
    df["AgeBin"] = "Adult"
    df["HasCabin"] = 0
    df["Deck"] = "Unknown"
    df["Embarked"] = "S"
    df["Sex"] = 1 if input_data["Sex"] == "male" else 0

    for col in ["Age", "Fare"]:
        df[col] = imptr.transform(df[[col]])[0][0]

    for col in ["Title", "FareBin", "AgeBin", "Deck", "Embarked"]:
        if col in encoders:
            val = df[col].astype(str).values[0]
            df[col] = encoders[col].transform([val])[0] if val in encoders[col].classes_ else 0

    X_input = scaler.transform(df[features].values.reshape(1, -1))
    proba = model.predict_proba(X_input)[0][1]
    return proba


def main():
    st.title("🚢 Titanic Survival Predictor")
    st.markdown("Interactive ML dashboard for the Titanic: Machine Learning from Disaster competition.")

    with st.spinner("Loading data and training models..."):
        df = load_data()
        models, scaler, encoders, imptr, features, results_df, X_val, y_val = train_models(df)

    tab1, tab2, tab3, tab4 = st.tabs(
        ["🔮 Predict", "📊 Model Comparison", "📈 Feature Analysis", "📋 Data Explorer"]
    )

    with tab1:
        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("Passenger Details")
            pclass = st.selectbox("Passenger Class", [1, 2, 3], format_func=lambda x: f"{x} ({['First','Business','Economy'][x-1]})")
            sex = st.selectbox("Sex", ["male", "female"])
            age = st.slider("Age", 0, 100, 30)
            sibsp = st.number_input("Siblings/Spouses Aboard", 0, 10, 0)
            parch = st.number_input("Parents/Children Aboard", 0, 10, 0)
            fare = st.number_input("Fare (£)", 0.0, 600.0, 50.0, step=5.0)
            model_choice = st.selectbox("Model", list(models.keys()))

            input_data = {
                "Pclass": pclass, "Sex": sex, "Age": age,
                "SibSp": sibsp, "Parch": parch, "Fare": fare,
            }

            if st.button("Predict Survival", type="primary"):
                proba = predict_survival(
                    models[model_choice], scaler, encoders, imptr, features, input_data
                )
                survived = proba >= 0.5

                col_res1, col_res2 = st.columns(2)
                with col_res1:
                    if survived:
                        st.success(f"### ✅ Survived ({proba:.1%} confidence)")
                    else:
                        st.error(f"### ❌ Did Not Survive ({1-proba:.1%} confidence)")

                with col_res2:
                    fig = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=proba * 100,
                        domain={"x": [0, 1], "y": [0, 1]},
                        title={"text": "Survival Probability (%)"},
                        gauge={
                            "axis": {"range": [0, 100]},
                            "bar": {"color": "green" if survived else "red"},
                            "steps": [
                                {"range": [0, 50], "color": "#ffcccc"},
                                {"range": [50, 100], "color": "#ccffcc"},
                            ],
                        },
                    ))
                    fig.update_layout(height=250)
                    st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Feature Values")
            st.json(input_data)
            st.caption(f"Model used: **{model_choice}**")

    with tab2:
        st.subheader("Model Performance Comparison")

        col1, col2 = st.columns([1, 1])
        with col1:
            st.dataframe(results_df, use_container_width=True, hide_index=True)

        with col2:
            fig = px.bar(
                results_df, x="Model", y="Accuracy", color="Model",
                title="Accuracy by Model", text="Accuracy"
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("ROC Curves")
        fig, ax = plt.subplots(figsize=(8, 5))
        for name, model in models.items():
            if hasattr(model, "predict_proba"):
                proba = model.predict_proba(X_val)[:, 1]
                fpr, tpr, _ = roc_curve(y_val, proba)
                auc = roc_auc_score(y_val, proba)
                ax.plot(fpr, tpr, label=f"{name} (AUC={auc:.3f})")
        ax.plot([0, 1], [0, 1], "k--", alpha=0.5)
        ax.set_xlabel("False Positive Rate")
        ax.set_ylabel("True Positive Rate")
        ax.set_title("ROC Curves")
        ax.legend()
        st.pyplot(fig)

    with tab3:
        st.subheader("Feature Importance")
        rf = models["Random Forest"]
        imp_df = pd.DataFrame({"Feature": features, "Importance": rf.feature_importances_})
        imp_df = imp_df.sort_values("Importance", ascending=True)

        fig = px.bar(imp_df.tail(12), x="Importance", y="Feature",
                     orientation="h", title="Top 12 Feature Importances (Random Forest)",
                     color="Importance", color_continuous_scale="Blues")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Confusion Matrix")
        preds = models["Ensemble"].predict(X_val)
        cm = confusion_matrix(y_val, preds)
        fig_cm = px.imshow(cm, text_auto=True, color_continuous_scale="Blues",
                           labels=dict(x="Predicted", y="Actual", color="Count"),
                           x=["Died", "Survived"], y=["Died", "Survived"])
        fig_cm.update_layout(height=400)
        st.plotly_chart(fig_cm, use_container_width=True)

    with tab4:
        st.subheader("Training Data Explorer")
        col1, col2 = st.columns([1, 3])
        with col1:
            filter_sex = st.multiselect("Sex", df["Sex"].unique(), default=df["Sex"].unique())
            filter_pclass = st.multiselect("Pclass", sorted(df["Pclass"].unique()), default=sorted(df["Pclass"].unique()))
        with col2:
            filtered = df[(df["Sex"].isin(filter_sex)) & (df["Pclass"].isin(filter_pclass))]
            st.dataframe(filtered.head(100), use_container_width=True, hide_index=True)
            st.caption(f"Showing {min(100, len(filtered))} of {len(filtered)} rows")


if __name__ == "__main__":
    main()
