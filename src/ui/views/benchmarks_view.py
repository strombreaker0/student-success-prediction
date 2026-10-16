"""
Model Evaluation & Benchmarks View.
Visualizes comparative performance metrics, ROC-AUC curves, and confusion matrices
from serialized benchmark artifacts.
"""

import os
import json
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MODELS_DIR = os.path.join(BASE_DIR, 'models')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports', 'figures')


def render_benchmarks_view():
    st.subheader("Supervised ML Benchmark Comparison")
    st.write("Comprehensive evaluation of Logistic Regression, Decision Tree, and Random Forest on an independent test cohort (240 samples, 80/20 stratified split).")

    metrics_path = os.path.join(MODELS_DIR, 'evaluation_metrics.json')
    if not os.path.exists(metrics_path):
        st.warning(f"Metrics artifact not found at {metrics_path}. Please execute `python src/train_models.py`.")
        return

    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    # Convert to DataFrame
    metrics_df = pd.DataFrame(metrics).T
    metrics_df.columns = ['Accuracy', 'Precision', 'Recall', 'F1-Score', 'ROC-AUC', 'Confusion Matrix']

    # Formatted Benchmark Table
    st.markdown("#### Performance Metric Summary")
    st.dataframe(
        metrics_df[['Accuracy', 'Precision', 'Recall', 'F1-Score', 'ROC-AUC']].style.format("{:.2%}"),
        use_container_width=True
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Accuracy & F1-Score Comparison")
        fig, ax = plt.subplots(figsize=(6.5, 4))
        plot_df = metrics_df[['Accuracy', 'F1-Score']].reset_index()
        plot_df = pd.melt(plot_df, id_vars=['index'], value_vars=['Accuracy', 'F1-Score'], var_name='Metric', value_name='Score')
        sns.barplot(data=plot_df, x='index', y='Score', hue='Metric', palette=['#1e3a8a', '#059669'], ax=ax)
        ax.set_ylim(0.5, 1.0)
        ax.set_ylabel("Score", fontsize=10)
        ax.set_xlabel("Algorithm", fontsize=10)
        ax.set_title("Test Cohort Benchmark Scores", weight='bold', fontsize=11)
        for p in ax.patches:
            val = p.get_height()
            if val > 0:
                ax.annotate(f"{val*100:.1f}%", (p.get_x() + p.get_width() / 2., val),
                            ha='center', va='bottom', fontsize=8.5, xytext=(0, 3), textcoords='offset points')
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    with col2:
        st.markdown("##### Receiver Operating Characteristic (ROC)")
        roc_path = os.path.join(REPORTS_DIR, '6_roc_curves.png')
        if os.path.exists(roc_path):
            st.image(roc_path, caption="ROC Curves Across Evaluated Classifiers", use_container_width=True)
        else:
            st.info("ROC Curve graphic available at `reports/figures/6_roc_curves.png`.")

    st.markdown("---")
    st.markdown("##### Confusion Matrices")
    cm_path = os.path.join(REPORTS_DIR, '5_confusion_matrices.png')
    if os.path.exists(cm_path):
        st.image(cm_path, caption="Confusion Matrices Across Tested Algorithms", use_container_width=True)
    else:
        st.info("Confusion matrix graphic available at `reports/figures/5_confusion_matrices.png`.")
