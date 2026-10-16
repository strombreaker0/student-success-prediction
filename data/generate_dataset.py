"""
Student Performance Dataset Generator
Generates realistic student behavioral and academic data for machine learning classification.
Author: Asmita Chandram Kumbar (SYBSc CS, Roll No: SI1161)
"""

import numpy as np
import pandas as pd
import os

def generate_student_dataset(num_samples=1200, random_state=42):
    np.random.seed(random_state)
    
    # 1. Student ID
    student_ids = [f"STU_{1000 + i}" for i in range(num_samples)]
    
    # 2. Key Behavioral & Academic Features
    # Attendance Rate (%): Bounded between 40% and 100%, mean around 75%
    attendance_rate = np.clip(np.random.normal(loc=76.0, scale=12.5, size=num_samples), 40.0, 100.0)
    
    # Study Hours per Week: Bounded between 2 and 35 hours, mean around 14 hours
    study_hours_per_week = np.clip(np.random.normal(loc=14.0, scale=6.0, size=num_samples), 2.0, 35.0)
    
    # Previous Exam Score (out of 100): Mean around 65
    previous_scores = np.clip(np.random.normal(loc=64.0, scale=14.0, size=num_samples), 30.0, 98.0)
    
    # Assignments Completion Rate (%): Bounded between 30% and 100%
    assignment_completion_rate = np.clip(np.random.normal(loc=80.0, scale=15.0, size=num_samples), 30.0, 100.0)
    
    # Tutoring Sessions Attended (0 to 10 sessions)
    tutoring_sessions = np.random.poisson(lam=2.5, size=num_samples)
    tutoring_sessions = np.clip(tutoring_sessions, 0, 10)
    
    # Sleep Hours per Night: Bounded between 4 and 10 hours
    sleep_hours = np.clip(np.random.normal(loc=6.8, scale=1.1, size=num_samples), 4.0, 10.0)
    
    # Extracurricular Participation: 0 = No, 1 = Yes
    extracurricular = np.random.choice([0, 1], size=num_samples, p=[0.45, 0.55])
    
    # Internet Access at Home: 0 = No, 1 = Yes
    internet_access = np.random.choice([0, 1], size=num_samples, p=[0.10, 0.90])

    # 3. Latent Academic Performance Score Calculation
    # Weighted combination of features + random variance (simulating real-world test unpredictability)
    z = (
        0.045 * attendance_rate +
        0.090 * study_hours_per_week +
        0.050 * previous_scores +
        0.025 * assignment_completion_rate +
        0.180 * tutoring_sessions +
        0.080 * (sleep_hours - 6.5) +  # optimal sleep around 7-8h
        0.200 * extracurricular +
        0.250 * internet_access -
        9.80  # Bias/Intercept to balance pass rate around 70-75%
    )
    
    # Sigmoid function to derive pass probability
    probabilities = 1 / (1 + np.exp(-z))
    
    # Stochastic binary outcome based on probability
    passed = (np.random.rand(num_samples) < probabilities).astype(int)
    
    # Final Exam Score (out of 100) strongly correlated with z
    final_score = np.clip(45 + z * 8 + np.random.normal(0, 5, num_samples), 20.0, 99.0)
    
    df = pd.DataFrame({
        'student_id': student_ids,
        'attendance_rate': np.round(attendance_rate, 2),
        'study_hours_per_week': np.round(study_hours_per_week, 1),
        'previous_scores': np.round(previous_scores, 2),
        'assignment_completion_rate': np.round(assignment_completion_rate, 2),
        'tutoring_sessions': tutoring_sessions,
        'sleep_hours': np.round(sleep_hours, 1),
        'extracurricular': extracurricular,
        'internet_access': internet_access,
        'final_exam_score': np.round(final_score, 2),
        'passed': passed
    })
    
    # Introduce small realistic missing values (MCAR) in raw data to demonstrate data cleaning
    missing_indices = np.random.choice(num_samples, size=int(num_samples * 0.03), replace=False)
    df.loc[missing_indices[:len(missing_indices)//2], 'attendance_rate'] = np.nan
    df.loc[missing_indices[len(missing_indices)//2:], 'study_hours_per_week'] = np.nan

    return df

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(base_dir, exist_ok=True)
    csv_path = os.path.join(base_dir, 'student_data.csv')
    
    df = generate_student_dataset()
    df.to_csv(csv_path, index=False)
    print(f"Dataset successfully created at: {csv_path}")
    print(f"Total Records: {len(df)}")
    print(f"Pass/Fail Distribution:\n{df['passed'].value_counts(normalize=True)}")
    print(f"Missing Values:\n{df.isnull().sum()}")
