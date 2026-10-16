"""
Exploratory Data Analysis (EDA) and Visualization Suite
Generates high-resolution academic figures for reports and presentations.
Author: Asmita Chandram Kumbar (SYBSc CS, Roll No: SI1161)
"""

import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import joblib
from sklearn.metrics import confusion_matrix, roc_curve, auc

def generate_eda_figures(data_dict, models_dir, reports_dir):
    os.makedirs(reports_dir, exist_ok=True)
    sns.set_theme(style='whitegrid', palette='muted')
    plt.rcParams.update({'font.sans-serif': 'Arial', 'font.size': 11})

    df = data_dict['df']
    X_test = data_dict['X_test']
    y_test = data_dict['y_test']
    
    # 1. Attendance Rate vs Exam Outcome (Boxplot & Strip plot)
    plt.figure(figsize=(8, 6))
    ax = sns.boxplot(x='passed', y='attendance_rate', data=df, palette=['#e74c3c', '#2ecc71'])
    sns.stripplot(x='passed', y='attendance_rate', data=df, color='black', alpha=0.2, jitter=0.2)
    plt.title('Student Attendance Rate by Exam Outcome (Pass vs Fail)', fontsize=14, weight='bold', pad=12)
    plt.xlabel('Exam Outcome (0 = Fail, 1 = Pass)', fontsize=12)
    plt.ylabel('Attendance Rate (%)', fontsize=12)
    plt.xticks([0, 1], ['Failed', 'Passed'])
    plt.tight_layout()
    fig1_path = os.path.join(reports_dir, '1_attendance_vs_outcome.png')
    plt.savefig(fig1_path, dpi=300)
    plt.close()
    print(f"[EDA] Saved: {fig1_path}")

    # 2. Weekly Study Hours vs Final Exam Score (Scatter with Regression Line)
    plt.figure(figsize=(9, 6))
    sns.regplot(
        x='study_hours_per_week', 
        y='final_exam_score', 
        data=df,
        scatter_kws={'alpha': 0.5, 'color': '#3498db'},
        line_kws={'color': '#e74c3c', 'linewidth': 2}
    )
    plt.title('Relationship: Weekly Study Hours vs Final Exam Score', fontsize=14, weight='bold', pad=12)
    plt.xlabel('Weekly Study Hours', fontsize=12)
    plt.ylabel('Final Exam Score (0 - 100)', fontsize=12)
    plt.tight_layout()
    fig2_path = os.path.join(reports_dir, '2_study_hours_vs_score.png')
    plt.savefig(fig2_path, dpi=300)
    plt.close()
    print(f"[EDA] Saved: {fig2_path}")

    # 3. Correlation Heatmap
    plt.figure(figsize=(10, 8))
    numeric_cols = [
        'attendance_rate', 'study_hours_per_week', 'previous_scores',
        'assignment_completion_rate', 'tutoring_sessions', 'sleep_hours',
        'extracurricular', 'internet_access', 'passed'
    ]
    corr = df[numeric_cols].corr()
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(corr, annot=True, fmt='.2f', cmap='Blues', mask=mask, cbar_kws={'shrink': .8})
    plt.title('Correlation Matrix of Student Behavioral Metrics', fontsize=14, weight='bold', pad=12)
    plt.tight_layout()
    fig3_path = os.path.join(reports_dir, '3_correlation_matrix.png')
    plt.savefig(fig3_path, dpi=300)
    plt.close()
    print(f"[EDA] Saved: {fig3_path}")

    # 4. Logistic Regression Feature Importance / Odds Ratio
    log_reg_path = os.path.join(models_dir, 'logistic_regression_model.joblib')
    if os.path.exists(log_reg_path):
        log_reg = joblib.load(log_reg_path)
        feature_names = [
            'Attendance Rate', 'Study Hours', 'Previous Scores',
            'Assignment Completion', 'Tutoring Sessions', 'Sleep Hours',
            'Extracurricular', 'Internet Access'
        ]
        coefs = log_reg.coef_[0]
        sorted_indices = np.argsort(coefs)
        
        plt.figure(figsize=(9, 6))
        colors = ['#2ecc71' if c > 0 else '#e74c3c' for c in coefs[sorted_indices]]
        plt.barh([feature_names[i] for i in sorted_indices], coefs[sorted_indices], color=colors)
        plt.axvline(0, color='grey', linestyle='--', linewidth=0.8)
        plt.title('Logistic Regression Standardized Feature Weights (Impact on Passing)', fontsize=13, weight='bold', pad=12)
        plt.xlabel('Standardized Coefficient Weight (Log-Odds Impact)', fontsize=11)
        plt.tight_layout()
        fig4_path = os.path.join(reports_dir, '4_feature_coefficients.png')
        plt.savefig(fig4_path, dpi=300)
        plt.close()
        print(f"[EDA] Saved: {fig4_path}")

    # 5. Confusion Matrices for Models
    model_files = {
        'Logistic Regression': os.path.join(models_dir, 'logistic_regression_model.joblib'),
        'Decision Tree': os.path.join(models_dir, 'decision_tree_model.joblib'),
        'Random Forest': os.path.join(models_dir, 'random_forest_model.joblib')
    }
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for i, (name, path) in enumerate(model_files.items()):
        if os.path.exists(path):
            model = joblib.load(path)
            y_pred = model.predict(X_test)
            cm = confusion_matrix(y_test, y_pred)
            sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[i],
                        xticklabels=['Fail (0)', 'Pass (1)'],
                        yticklabels=['Fail (0)', 'Pass (1)'], cbar=False)
            axes[i].set_title(f'{name}\nConfusion Matrix', weight='bold')
            axes[i].set_xlabel('Predicted Label')
            axes[i].set_ylabel('True Label')
            
    plt.tight_layout()
    fig5_path = os.path.join(reports_dir, '5_confusion_matrices.png')
    plt.savefig(fig5_path, dpi=300)
    plt.close()
    print(f"[EDA] Saved: {fig5_path}")

    # 6. ROC Curves Comparison
    plt.figure(figsize=(8, 6))
    for name, path in model_files.items():
        if os.path.exists(path):
            model = joblib.load(path)
            if hasattr(model, 'predict_proba'):
                probs = model.predict_proba(X_test)[:, 1]
                fpr, tpr, _ = roc_curve(y_test, probs)
                roc_auc = auc(fpr, tpr)
                plt.plot(fpr, tpr, label=f'{name} (AUC = {roc_auc:.3f})', linewidth=2)
                
    plt.plot([0, 1], [0, 1], 'k--', label='Random Classifier (AUC = 0.500)')
    plt.xlabel('False Positive Rate (1 - Specificity)', fontsize=11)
    plt.ylabel('True Positive Rate (Sensitivity / Recall)', fontsize=11)
    plt.title('Receiver Operating Characteristic (ROC) Curves', fontsize=14, weight='bold', pad=12)
    plt.legend(loc='lower right', frameon=True)
    plt.tight_layout()
    fig6_path = os.path.join(reports_dir, '6_roc_curves.png')
    plt.savefig(fig6_path, dpi=300)
    plt.close()
    print(f"[EDA] Saved: {fig6_path}")

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_file = os.path.join(base_dir, 'data', 'student_data.csv')
    models_dir = os.path.join(base_dir, 'models')
    reports_dir = os.path.join(base_dir, 'reports', 'figures')
    
    from preprocess import load_and_preprocess_data
    data = load_and_preprocess_data(csv_file)
    generate_eda_figures(data, models_dir, reports_dir)
