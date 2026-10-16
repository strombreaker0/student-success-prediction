# ACADEMIC PROJECT REPORT

## PROJECT TITLE:
### PREDICTING STUDENT ACADEMIC SUCCESS AND EXAM OUTCOMES USING SUPERVISED MACHINE LEARNING

---

### CANDIDATE CREDENTIALS
* **Name of Candidate:** Asmita Chandram Kumbar  
* **Class / Semester:** Second Year Bachelor of Science - Computer Science (SYBSc CS)  
* **Academic Year:** 2nd Year  
* **Roll Number:** SI1161  
* **Department:** Department of Computer Science  

---

## 1. ABSTRACT
Educational data mining (EDM) is a transformative discipline that converts institutional educational data into actionable pedagogical intelligence. This project addresses student academic underachievement through proactive predictive modeling. Utilizing supervised machine learning classification algorithms, an automated decision-support pipeline was built and validated on a student cohort with behavioral, attendance, and coursework metrics. 

Logistic Regression, Decision Tree, and Random Forest classifiers were evaluated across standard performance criteria including Accuracy, Precision, Recall, F1-Score, and ROC-AUC. Logistic Regression achieved an optimal test accuracy of **80.00%** with an ROC-AUC of **0.8495** and an exceptional Recall of **90.62%**. To translate predictive insights into practical educational utility, an interactive Streamlit graphical user interface and command-line prediction interface were engineered. The system provides instantaneous risk stratification and suggests personalized remedial interventions, empowering educators to prevent exam failure before it occurs.

---

## 2. INTRODUCTION & BACKGROUND
Academic failure incurs substantial emotional and financial costs to students and institutions. Historically, educational institutions employ post-facto evaluations (such as mid-semester grade sheets) to track progress. By the time grades reflect poor understanding, students often lack sufficient time to recover.

Machine learning offers the capability to discern non-linear associations between daily academic habits and term-end examination outcomes. By continuously modeling behavioral markers—including attendance percentage, self-study duration, assignment completion rate, and tutoring attendance—predictive algorithms can forecast student trajectory with high statistical reliability.

---

## 3. PROBLEM STATEMENT
> *"Development of an automated classification model to predict whether a student will pass or fail an examination based on key behavioral metrics, enabling early intervention for at-risk learners."*

---

## 4. SYSTEM ARCHITECTURE & METHODOLOGY

```
+-------------------------------------------------------------+
|                 1. Data Collection & Schema                 |
|  - Attendance Rate (%)         - Study Hours / Week         |
|  - Previous Exam Score (%)     - Assignment Completion (%)  |
|  - Tutoring Sessions Attended  - Sleep Hours / Night        |
|  - Extracurricular (0/1)       - Internet Access (0/1)      |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|               2. Data Preprocessing & Cleaning              |
|  - Missing Value Imputation (Median Strategy)               |
|  - Stratified 80/20 Train-Test Splitting                    |
|  - Standard Scaling: Z = (X - μ) / σ                        |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|               3. Supervised Model Training                  |
|  - Logistic Regression Classifier                           |
|  - Decision Tree Classifier                                 |
|  - Random Forest Ensemble Classifier                        |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|           4. Model Evaluation & Comparative Metrics         |
|  - Accuracy, Precision, Recall, F1-Score                    |
|  - Confusion Matrices & ROC-AUC Curves                      |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                 5. Prediction & Decision Tools              |
|  - Streamlit Interactive Web Application                    |
|  - Command-Line Interface (CLI) Prediction Tool             |
|  - Tailored Early Intervention Recommendation Engine        |
+-------------------------------------------------------------+
```

---

## 5. MATHEMATICAL FORMULATION

### 5.1 Logistic Regression
Logistic Regression models the posterior probability of class $Y=1$ (Pass) conditioned on the feature vector $\mathbf{x}$:
$$P(Y=1 \mid \mathbf{x}) = \sigma(\mathbf{w}^T \mathbf{x} + b) = \frac{1}{1 + e^{-(\mathbf{w}^T \mathbf{x} + b)}}$$

Where:
* $\mathbf{w}$ denotes the learned weight vector for each behavioral metric.
* $b$ represents the bias/intercept term.
* The model minimizes the binary cross-entropy (Log-Loss) cost function:
$$J(\mathbf{w}, b) = -\frac{1}{N} \sum_{i=1}^N \left[ y^{(i)} \log(\hat{y}^{(i)}) + (1 - y^{(i)}) \log(1 - \hat{y}^{(i)}) \right]$$

### 5.2 Odds Ratio Interpretation
The exponential of the logistic regression coefficient represents the Odds Ratio ($OR = e^{w_j}$). For instance, for every standardized unit increase in weekly study hours ($w \approx 0.68$), the odds of passing increase by a factor of $e^{0.68} \approx 1.97$ (a $97\%$ increase in passing odds).

---

## 6. EXPERIMENTAL RESULTS

The dataset comprising 1,200 student records was partitioned into 960 training instances (80%) and 240 unseen testing instances (20%) using stratified sampling.

### 6.1 Performance Metric Summary Table

| Metric | Logistic Regression | Decision Tree | Random Forest |
| :--- | :---: | :---: | :---: |
| **Accuracy** | **80.00%** | 74.17% | 77.92% |
| **Precision** | **81.46%** | 75.52% | 78.01% |
| **Recall (Sensitivity)** | **90.62%** | 90.62% | **93.12%** |
| **F1-Score** | **85.80%** | 82.39% | 84.90% |
| **ROC-AUC** | **0.8495** | 0.7580 | 0.8274 |

### 6.2 Confusion Matrix (Logistic Regression on 240 Test Cases)
* **True Positives (TP):** 145 passing students accurately identified.
* **True Negatives (TN):** 47 failing students accurately identified.
* **False Positives (FP):** 33 students flagged as passing who failed.
* **False Negatives (FN):** 15 students flagged as failing who passed.

### 6.3 Key Analytical Findings
1. **Attendance vs. Study Hours**: Attendance rate and study hours exhibited the highest statistical correlation with exam success ($r = 0.58$ and $r = 0.64$ respectively).
2. **Threshold Effects**: Students with attendance below **75%** and study hours below **10 hours/week** suffered a failure rate exceeding **72%**.
3. **Remedial Tutoring**: Students who attended 3 or more remedial tutoring sessions exhibited a 31% recovery rate from prior poor performance.

---

## 7. USER INTERFACE & IMPLEMENTATION FEATURES

1. **Real-Time Prediction Interface**:
   - Sliders and interactive inputs for all 8 behavioral dimensions.
   - Dynamic probability bar and visual risk categorization (Low Risk / Safe, Moderate Risk, High Risk).
2. **Personalized Academic Intervention Generator**:
   - Identifies specific metric deficiencies (e.g., attendance $< 75\%$, study deficit $< 12$ hrs/week).
   - Generates customized recommendations for academic advisors and tutors.
3. **Batch Screening System**:
   - Allows upload of class CSV rosters.
   - Automatically ranks and highlights at-risk students for cohort-wide intervention.
   - One-click export of screened intervention rosters.

---

## 8. HARDWARE & SOFTWARE SPECIFICATIONS

* **Operating System:** Windows 10/11 / macOS / Linux
* **Language:** Python 3.8+ (tested on Python 3.14)
* **Key Libraries:**
  - `numpy`, `pandas`: Data structuring and mathematical operations.
  - `scikit-learn`: Preprocessing, model training, and performance metrics.
  - `matplotlib`, `seaborn`: Visualization and publication-quality plots.
  - `streamlit`: Web application framework.
  - `joblib`: Serialization of trained models and scalers.

---

## 9. CONCLUSION & FUTURE SCOPE
The developed supervised machine learning system successfully fulfills all objectives set forth in the project synopsis. It transitions academic support from a reactive model to an actionable, proactive framework. 

**Future Enhancements:**
1. Integration with College Learning Management Systems (LMS) such as Moodle or Google Classroom for automated attendance and assignment sync.
2. Deployment of Deep Neural Network architectures as larger historical datasets become available.
3. Automated email or SMS alert dispatch to students and faculty mentors when risk indices exceed critical thresholds.

---
**Submitted by:** Asmita Chandram Kumbar  
**Roll No:** SI1161 | **Class:** SYBSc CS (2nd Year)
