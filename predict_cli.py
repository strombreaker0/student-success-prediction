"""
Command-Line Prediction Tool
Allows educators and students to enter behavioral metrics and receive instant pass/fail predictions.
Author: Asmita Chandram Kumbar (SYBSc CS, Roll No: SI1161)
"""

import os
import joblib
import numpy as np

def load_system(models_dir):
    imputer_path = os.path.join(models_dir, 'imputer.joblib')
    scaler_path = os.path.join(models_dir, 'scaler.joblib')
    model_path = os.path.join(models_dir, 'logistic_regression_model.joblib')
    
    if not (os.path.exists(imputer_path) and os.path.exists(scaler_path) and os.path.exists(model_path)):
        raise FileNotFoundError("Trained models or preprocessors not found! Please run train_models.py first.")
        
    imputer = joblib.load(imputer_path)
    scaler = joblib.load(scaler_path)
    model = joblib.load(model_path)
    
    return imputer, scaler, model

def get_input(prompt, default, val_type=float, min_val=None, max_val=None):
    while True:
        user_val = input(f"{prompt} [Default: {default}]: ").strip()
        if not user_val:
            return default
        try:
            val = val_type(user_val)
            if min_val is not None and val < min_val:
                print(f"  [!] Value must be >= {min_val}. Try again.")
                continue
            if max_val is not None and val > max_val:
                print(f"  [!] Value must be <= {max_val}. Try again.")
                continue
            return val
        except ValueError:
            print("  [!] Invalid format. Please enter a valid number.")

def main():
    print("=" * 65)
    print("  STUDENT ACADEMIC SUCCESS PREDICTION TOOL (CLI)  ")
    print("  Author: Asmita Chandram Kumbar | SYBSc CS | Roll: SI1161")
    print("=" * 65)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(base_dir, 'models')
    
    try:
        imputer, scaler, model = load_system(models_dir)
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    print("\nPlease enter the student's behavioral and academic metrics:")
    
    attendance = get_input("1. Attendance Rate (0 - 100%)", 75.0, float, 0.0, 100.0)
    study_hours = get_input("2. Weekly Study Hours (0 - 50 hrs)", 14.0, float, 0.0, 50.0)
    prev_scores = get_input("3. Previous Exam Scores (0 - 100)", 65.0, float, 0.0, 100.0)
    assignments = get_input("4. Assignment Completion Rate (0 - 100%)", 80.0, float, 0.0, 100.0)
    tutoring = get_input("5. Tutoring Sessions Attended (0 - 20)", 2, int, 0, 20)
    sleep = get_input("6. Average Sleep Hours / Night (3 - 12 hrs)", 7.0, float, 3.0, 12.0)
    extra = get_input("7. Extracurricular Participation (1 for Yes, 0 for No)", 1, int, 0, 1)
    internet = get_input("8. Internet Access at Home (1 for Yes, 0 for No)", 1, int, 0, 1)
    
    # Structure input DataFrame with feature names
    feature_cols = [
        'attendance_rate', 'study_hours_per_week', 'previous_scores',
        'assignment_completion_rate', 'tutoring_sessions', 'sleep_hours',
        'extracurricular', 'internet_access'
    ]
    raw_df = pd.DataFrame([[
        attendance, study_hours, prev_scores, assignments,
        tutoring, sleep, extra, internet
    ]], columns=feature_cols)
    
    # Preprocess & scale
    imputed_features = imputer.transform(raw_df)
    scaled_features = scaler.transform(imputed_features)
    
    # Inference
    prediction = model.predict(scaled_features)[0]
    probabilities = model.predict_proba(scaled_features)[0]
    pass_prob = probabilities[1] * 100
    fail_prob = probabilities[0] * 100
    
    print("\n" + "=" * 65)
    print("                     EVALUATION REPORT                     ")
    print("=" * 65)
    
    if prediction == 1:
        print(f"\n[+] OUTCOME: PREDICTED TO PASS (Probability: {pass_prob:.2f}%)")
        if pass_prob >= 80:
            print("[+] ACADEMIC STATUS: Distinction / Strong Candidate")
            print("[+] RECOMMENDATION: Maintain current study habits and consistent attendance.")
        else:
            print("[+] ACADEMIC STATUS: Safe, but moderate risk of slipping.")
            print("[+] RECOMMENDATION: Increase study hours slightly to guarantee upper grade bands.")
    else:
        print(f"\n[-] OUTCOME: PREDICTED TO FAIL (Failure Risk: {fail_prob:.2f}%)")
        print("[-] ACADEMIC STATUS: AT-RISK STUDENT (Requires Early Intervention)")
        print("\n[!] RECOMMENDED TIMELY INTERVENTIONS:")
        if attendance < 75:
            print("  * Attendance Warning: Attendance is below 75%. Schedule a counseling session.")
        if study_hours < 10:
            print(f"  * Study Hours Deficit: Current ({study_hours} hrs/week). Recommend increasing by +5 hrs/week.")
        if assignments < 70:
            print("  * Assignment Catch-up: Student has missing submissions. Assign peer tutoring.")
        if tutoring < 2:
            print("  * Remedial Tutoring: Enroll student in weekly remedial classes.")
            
    print("=" * 65 + "\n")

if __name__ == '__main__':
    main()
