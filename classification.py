"""
Advanced Match Winner Classification for IPL Cricket Data Mining Project.

This module trains and compares four classification models (Random Forest,
Gradient Boosting, Logistic Regression, SVM) to predict IPL match winners
using engineered features. Implements cross-validation, SHAP explanations,
and confidence-calibrated predictions.

Outputs:
    - datasets/match_predictions_advanced.csv
    - plots/shap_feature_importance.png
"""

import os
import warnings
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, classification_report

warnings.filterwarnings('ignore', category=FutureWarning)


def load_enriched_match_data():
    """Load the enriched match features from feature engineering."""
    path = 'datasets/enriched_match_features.csv'
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found. Run feature_engineering.py first."
        )
    df = pd.read_csv(path)
    print(f"[✓] Loaded enriched match features: {df.shape}")
    return df


def prepare_features(df):
    """
    Prepare feature matrix and target variable.
    Encodes categorical variables and scales numerical features.

    Returns: X, y, feature_names, label_encoder, scaler
    """
    # Filter out rare winners (< 10 matches won)
    winner_counts = df['winner'].value_counts()
    valid_teams = winner_counts[winner_counts >= 10].index
    df = df[df['winner'].isin(valid_teams)].copy()

    print(f"[✓] After filtering rare teams: {len(df)} matches, {len(valid_teams)} teams")

    # Target encoding
    le = LabelEncoder()
    y = le.fit_transform(df['winner'])

    # Feature columns: mix of categorical (one-hot) and numerical (engineered)
    numerical_features = [
        'h2h_team1_win_pct', 'avg_runs_per_match',
        'venue_win_pct_team1', 'venue_win_pct_team2',
        'form_team1', 'form_team2', 'toss_winner_won'
    ]

    # Keep only available numerical features
    num_feats = [f for f in numerical_features if f in df.columns]

    # Categorical features: one-hot encode team1, team2, toss_winner, toss_decision, venue
    cat_cols = ['team1', 'team2', 'toss_winner', 'toss_decision', 'venue']
    cat_cols = [c for c in cat_cols if c in df.columns]

    df_encoded = pd.get_dummies(df[cat_cols], columns=cat_cols)

    # Combine numerical + categorical
    X = pd.concat([df[num_feats].reset_index(drop=True),
                    df_encoded.reset_index(drop=True)], axis=1)

    # Handle missing values
    X = X.fillna(0)

    # Scale numerical features
    scaler = StandardScaler()
    X[num_feats] = scaler.fit_transform(X[num_feats])

    feature_names = list(X.columns)
    print(f"[✓] Feature matrix: {X.shape} ({len(num_feats)} numerical + {X.shape[1] - len(num_feats)} categorical)")

    return X, y, feature_names, le, scaler


def build_models():
    """
    Build a dictionary of models to compare.
    Returns dict of {name: model_instance}.
    """
    models = {
        'Random Forest': RandomForestClassifier(
            n_estimators=200, max_depth=15, random_state=42, n_jobs=-1
        ),
        'Gradient Boosting': GradientBoostingClassifier(
            n_estimators=150, max_depth=5, learning_rate=0.1, random_state=42
        ),
        'Logistic Regression': LogisticRegression(
            max_iter=1000, random_state=42, C=1.0, solver='lbfgs'
        ),
        'SVM': SVC(
            kernel='rbf', C=1.0, gamma='scale', probability=True, random_state=42
        )
    }
    print(f"[✓] Built {len(models)} models for comparison")
    return models


def cross_validate_models(models, X, y):
    """
    Perform 5-fold Stratified Cross-Validation on all models.
    Returns a comparison DataFrame.
    """
    print("\n── 5-Fold Stratified Cross-Validation ──")
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    results = []
    for name, model in models.items():
        scores = cross_val_score(model, X, y, cv=skf, scoring='accuracy', n_jobs=-1)
        results.append({
            'Model': name,
            'CV Accuracy Mean': round(scores.mean(), 4),
            'CV Accuracy Std': round(scores.std(), 4),
        })
        print(f"  {name}: {scores.mean():.4f} ± {scores.std():.4f}")

    return pd.DataFrame(results)


def train_and_evaluate(models, X_train, X_test, y_train, y_test, cv_results):
    """
    Train all models on training set, evaluate on test set.
    Updates cv_results with test accuracy. Returns trained models dict.
    """
    print("\n── Training & Test Evaluation ──")
    trained = {}
    test_accuracies = []

    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        test_accuracies.append(round(acc, 4))
        trained[name] = model
        print(f"  {name}: Test Accuracy = {acc:.4f}")

    cv_results['Test Accuracy'] = test_accuracies
    return trained, cv_results


def print_comparison_table(cv_results):
    """Print a formatted comparison table of all models."""
    print("\n══════════════════════════════════════════════════════════════")
    print("  MODEL COMPARISON TABLE")
    print("══════════════════════════════════════════════════════════════")
    print(f"  {'Model':<25} {'CV Mean':<12} {'CV Std':<12} {'Test Acc':<10}")
    print(f"  {'─'*59}")
    for _, row in cv_results.iterrows():
        print(f"  {row['Model']:<25} {row['CV Accuracy Mean']:<12.4f} "
              f"{row['CV Accuracy Std']:<12.4f} {row['Test Accuracy']:<10.4f}")
    print("══════════════════════════════════════════════════════════════")

    best = cv_results.loc[cv_results['Test Accuracy'].idxmax()]
    print(f"\n  🏆 Best Model: {best['Model']} (Test Accuracy: {best['Test Accuracy']:.4f})")


def explain_with_shap(model, X_train, X_test, feature_names, model_name):
    """
    Use SHAP values to explain the best model's predictions.
    Saves SHAP bar plot to plots/shap_feature_importance.png.
    """
    os.makedirs('plots', exist_ok=True)

    try:
        import shap

        print(f"\n── SHAP Feature Importance ({model_name}) ──")

        # Use appropriate explainer based on model type
        if isinstance(model, (RandomForestClassifier, GradientBoostingClassifier)):
            # Use TreeExplainer for tree-based models
            explainer = shap.TreeExplainer(model)
            # Use a sample of test data if large
            sample_size = min(100, X_test.shape[0])
            X_sample = X_test[:sample_size] if isinstance(X_test, np.ndarray) else X_test.iloc[:sample_size]
            shap_values = explainer.shap_values(X_sample)
        else:
            # Use KernelExplainer for other models
            sample_size = min(50, X_train.shape[0])
            background = X_train[:sample_size] if isinstance(X_train, np.ndarray) else X_train.iloc[:sample_size]
            explainer = shap.KernelExplainer(model.predict_proba, background)
            X_sample = X_test[:50] if isinstance(X_test, np.ndarray) else X_test.iloc[:50]
            shap_values = explainer.shap_values(X_sample)

        # Handle multi-class SHAP values (take mean absolute across classes)
        if isinstance(shap_values, list):
            # Multi-class: average across all classes
            shap_array = np.array(shap_values)
            mean_abs_shap = np.mean(np.abs(shap_array), axis=(0, 1))
        else:
            mean_abs_shap = np.mean(np.abs(shap_values), axis=0)

        # Get top 15 features
        if len(mean_abs_shap.shape) > 1:
            mean_abs_shap = np.mean(mean_abs_shap, axis=1)

        top_n = min(15, len(feature_names))
        top_indices = np.argsort(mean_abs_shap)[-top_n:]
        top_features = [feature_names[i] for i in top_indices]
        top_values = mean_abs_shap[top_indices]

        # Plot
        fig, ax = plt.subplots(figsize=(12, 8))
        colors = plt.cm.RdYlGn(np.linspace(0.2, 0.8, len(top_features)))
        ax.barh(range(len(top_features)), top_values, color=colors, edgecolor='white')
        ax.set_yticks(range(len(top_features)))
        ax.set_yticklabels(top_features, fontsize=11)
        ax.set_xlabel('Mean |SHAP Value|', fontsize=13)
        ax.set_title(f'SHAP Feature Importance – {model_name}', fontsize=15, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)

        fig.tight_layout()
        fig.savefig('plots/shap_feature_importance.png', dpi=150, bbox_inches='tight')
        plt.close(fig)
        print("[✓] SHAP plot saved to plots/shap_feature_importance.png")

    except ImportError:
        print("[⚠] SHAP library not available. Falling back to model feature importance.")
        _fallback_feature_importance(model, feature_names)
    except Exception as e:
        print(f"[⚠] SHAP analysis failed ({e}). Using fallback feature importance.")
        _fallback_feature_importance(model, feature_names)


def _fallback_feature_importance(model, feature_names):
    """Fallback: plot sklearn feature_importances_ if SHAP fails."""
    os.makedirs('plots', exist_ok=True)

    if hasattr(model, 'feature_importances_'):
        importances = model.feature_importances_
        top_n = min(15, len(feature_names))
        top_idx = np.argsort(importances)[-top_n:]
        top_feats = [feature_names[i] for i in top_idx]
        top_vals = importances[top_idx]

        fig, ax = plt.subplots(figsize=(12, 8))
        colors = plt.cm.RdYlGn(np.linspace(0.2, 0.8, len(top_feats)))
        ax.barh(range(len(top_feats)), top_vals, color=colors, edgecolor='white')
        ax.set_yticks(range(len(top_feats)))
        ax.set_yticklabels(top_feats, fontsize=11)
        ax.set_xlabel('Feature Importance', fontsize=13)
        ax.set_title('Feature Importance (sklearn)', fontsize=15, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)

        fig.tight_layout()
        fig.savefig('plots/shap_feature_importance.png', dpi=150, bbox_inches='tight')
        plt.close(fig)
        print("[✓] Fallback feature importance plot saved to plots/shap_feature_importance.png")


def save_predictions(model, X_test, y_test, le, feature_names, df_original):
    """
    Save predictions with confidence scores.
    """
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)

    # Get confidence of predicted class
    confidence = np.max(y_proba, axis=1) * 100

    results = pd.DataFrame({
        'Actual': le.inverse_transform(y_test),
        'Predicted': le.inverse_transform(y_pred),
        'Confidence_%': confidence.round(2),
        'Correct': (y_test == y_pred).astype(int)
    })

    results.to_csv('datasets/match_predictions_advanced.csv', index=False)
    print(f"\n[✓] Saved datasets/match_predictions_advanced.csv ({len(results)} predictions)")
    print(f"    Overall accuracy: {(results['Correct'].mean() * 100):.2f}%")
    print(f"    Average confidence: {results['Confidence_%'].mean():.2f}%")

    return results


# ── Main Pipeline ───────────────────────────────────────────────────────────────

def run_classification():
    """Run the full advanced classification pipeline."""
    os.makedirs('plots', exist_ok=True)

    # Load data
    df = load_enriched_match_data()

    # Prepare features
    X, y, feature_names, le, scaler = prepare_features(df)

    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"[✓] Train: {X_train.shape}, Test: {X_test.shape}")

    # Build models
    models = build_models()

    # Cross-validation
    cv_results = cross_validate_models(models, X, y)

    # Train and evaluate
    trained_models, cv_results = train_and_evaluate(
        models, X_train, X_test, y_train, y_test, cv_results
    )

    # Print comparison table
    print_comparison_table(cv_results)

    # Find best model
    best_name = cv_results.loc[cv_results['Test Accuracy'].idxmax(), 'Model']
    best_model = trained_models[best_name]

    # SHAP explanation
    explain_with_shap(best_model, X_train, X_test, feature_names, best_name)

    # Classification report for best model
    y_pred = best_model.predict(X_test)
    print(f"\n── Classification Report ({best_name}) ──")
    print(classification_report(y_test, y_pred,
                                target_names=le.classes_,
                                zero_division=0))

    # Save predictions
    results = save_predictions(best_model, X_test, y_test, le, feature_names, df)

    print("\n[✓] Advanced classification complete ✅")
    return trained_models, cv_results, le, scaler, feature_names


if __name__ == '__main__':
    run_classification()