"""
Local execution entrypoint for Windows PowerShell / VS Code.
Runs the AI-Based Student Performance Prediction Flask application.

Usage:
    python run_flask.py
"""

import os
from flask_app import create_app
from flask_app.config import DevelopmentConfig

app = create_app(DevelopmentConfig)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n=======================================================")
    print(f" AI-Based Student Performance Prediction System (Flask)")
    print(f" Candidate: Asmita Chandram Kumbar | SYBSc CS | SI1161")
    print(f" Local URL: http://127.0.0.1:{port}")
    print(f" Health Check: http://127.0.0.1:{port}/health")
    print(f"=======================================================\n")
    app.run(host='127.0.0.1', port=port, debug=True)
