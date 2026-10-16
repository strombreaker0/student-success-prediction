"""
Model Training & Evaluation Module
Implements Logistic Regression, Decision Tree, and Random Forest Classifiers.
Author: Asmita Chandram Kumbar (SYBSc CS, Roll No: SI1161)
"""

import os
import joblib
import json
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_auc_score, roc_curve
)
from preprocess import load_and_preprocess_data, save_preprocessors, FEATURE_COLS

def train_and_evaluate_models(data, models_dir):
    os.makedirs(models_dir, exist_ok=True)
    
    X_train = data['X_train']
    X_test = data['X_test']
    y_train = data['y_train']
    y_test = data['y_test']
    
    # Define models
    models = {
        'Logistic Regression': LogisticRegression(random_state=42, max_iter=1000),
        'Decision Tree': DecisionTreeClassifier(random_state=42, max_depth=5, min_samples_split=10),
        'Random Forest': RandomForestClassifier(random_state=42, n_estimators=100, max_depth=6)
    }
    
    results = {}
    
    print("\n" + "="*60)
    print("           MODEL TRAINING AND EVALUATION RESULTS           ")
    print("="*60)
    
    for name, model in models.items():
        # Fit model
        model.fit(X_train, y_train)
        
        # Predict on test set
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, 'predict_proba') else None
        
        # Metrics
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        roc_auc = roc_auc_score(y_test, y_prob) if y_prob is not None else 0.0
        cm = confusion_matrix(y_test, y_pred).tolist()
        
        results[name] = {
            'accuracy': round(float(acc), 4),
            'precision': round(float(prec), 4),
            'recall': round(float(rec), 4),
            'f1_score': round(float(f1), 4),
            'roc_auc': round(float(roc_auc), 4),
            'confusion_matrix': cm
        }
        
        # Save model
        clean_name = name.lower().replace(" ", "_")
        model_file = os.path.join(models_dir, f"{clean_name}_model.joblib")
        joblib.dump(model, model_file)
        
        print(f"\n--- Model: {name} ---")
        print(f"Accuracy:  {acc*100:.2f}%")
        print(f"Precision: {prec*100:.2f}%")
        print(f"Recall:    {rec*100:.2f}%")
        print(f"F1-Score:  {f1*100:.2f}%")
        print(f"ROC-AUC:   {roc_auc:.4f}")
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred, target_names=['Fail', 'Pass']))
        print("Confusion Matrix:")
        print(f"TN: {cm[0][0]}, FP: {cm[0][1]}")
        print(f"FN: {cm[1][0]}, TP: {cm[1][1]}")
        
    # Logistic Regression feature coefficients
    log_reg = models['Logistic Regression']
    coef_df = pd.DataFrame({
        'Feature': FEATURE_COLS,
        'Coefficient': log_reg.coef_[0],
        'Odds_Ratio': np.exp(log_reg.coef_[0])
    }).sort_values(by='Coefficient', ascending=False)
    
    coef_path = os.path.join(models_dir, 'logistic_regression_coefficients.csv')
    coef_df.to_csv(coef_path, index=False)
    
    # Save results summary JSON
    metrics_path = os.path.join(models_dir, 'evaluation_metrics.json')
    with open(metrics_path, 'w') as f:
        json.dump(results, f, indent=4)
        
    print(f"\n[Artifacts] Evaluation metrics saved to {metrics_path}")
    print(f"[Artifacts] Feature coefficients saved to {coef_path}")
    
    return results, models

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_file = os.path.join(base_dir, 'data', 'student_data.csv')
    models_dir = os.path.join(base_dir, 'models')
    
    data = load_and_preprocess_data(csv_file)
    save_preprocessors(data['imputer'], data['scaler'], models_dir)
    results, models = train_and_evaluate_models(data, models_dir)
