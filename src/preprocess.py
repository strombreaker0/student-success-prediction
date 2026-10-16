"""
Data Preprocessing and Pipeline Module
Handles missing values, feature selection, scaling, and train-test splitting.
Author: Asmita Chandram Kumbar (SYBSc CS, Roll No: SI1161)
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
import joblib
import os

FEATURE_COLS = [
    'attendance_rate',
    'study_hours_per_week',
    'previous_scores',
    'assignment_completion_rate',
    'tutoring_sessions',
    'sleep_hours',
    'extracurricular',
    'internet_access'
]

TARGET_COL = 'passed'

def load_and_preprocess_data(csv_path, test_size=0.20, random_state=42):
    """
    Loads raw student dataset, performs data cleaning/imputation,
    splits into train/test sets, and applies Standard Scaling.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found at {csv_path}")
    
    df = pd.read_csv(csv_path)
    print(f"[Preprocessing] Loaded dataset with shape {df.shape}")
    
    # Check and report missing values
    null_counts = df[FEATURE_COLS].isnull().sum()
    print("[Preprocessing] Missing values before imputation:")
    print(null_counts[null_counts > 0])
    
    # 1. Feature selection (ignore identifiers and target/dependent final scores)
    X = df[FEATURE_COLS].copy()
    y = df[TARGET_COL].copy()
    
    # 2. Train-test split (80% Train, 20% Test) with stratification
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    
    # 3. Handle missing values via Median Imputation (fit on train, transform on test)
    imputer = SimpleImputer(strategy='median')
    X_train_imputed = imputer.fit_transform(X_train)
    X_test_imputed = imputer.transform(X_test)
    
    # 4. Standard Scaling for numeric stability in Logistic Regression
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_imputed)
    X_test_scaled = scaler.transform(X_test_imputed)
    
    return {
        'df': df,
        'feature_cols': FEATURE_COLS,
        'target_col': TARGET_COL,
        'X_train_raw': X_train,
        'X_test_raw': X_test,
        'X_train': X_train_scaled,
        'X_test': X_test_scaled,
        'y_train': y_train.values,
        'y_test': y_test.values,
        'imputer': imputer,
        'scaler': scaler
    }

def save_preprocessors(imputer, scaler, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    imputer_path = os.path.join(output_dir, 'imputer.joblib')
    scaler_path = os.path.join(output_dir, 'scaler.joblib')
    joblib.dump(imputer, imputer_path)
    joblib.dump(scaler, scaler_path)
    print(f"[Preprocessing] Saved imputer to {imputer_path}")
    print(f"[Preprocessing] Saved scaler to {scaler_path}")

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_file = os.path.join(base_dir, 'data', 'student_data.csv')
    artifacts_dir = os.path.join(base_dir, 'models')
    
    data = load_and_preprocess_data(csv_file)
    save_preprocessors(data['imputer'], data['scaler'], artifacts_dir)
    print("[Preprocessing] Pipeline check passed!")
