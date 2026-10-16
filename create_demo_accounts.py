"""
Standalone CLI Script to Provision or Update Demo Accounts.

Usage:
    # Use environment variables or secure defaults:
    python create_demo_accounts.py

    # With custom passwords:
    python create_demo_accounts.py --admin-password "CustomAdmin#2026!" --student-password "CustomStudent#2026!"

    # Interactive mode (hidden password prompt):
    python create_demo_accounts.py --interactive
"""

import os
import sys
import argparse
import getpass
from src.services.demo_service import (
    provision_demo_accounts,
    DEMO_ADMIN_USERNAME,
    DEMO_STUDENT_USERNAME,
    DEMO_STUDENT_ID
)


def main():
    parser = argparse.ArgumentParser(description="Provision or update demo accounts safely and idempotently.")
    parser.add_argument("--admin-password", help="Custom password for demo admin account", default=None)
    parser.add_argument("--student-password", help="Custom password for demo student account", default=None)
    parser.add_argument("--interactive", action="store_true", help="Prompt for passwords securely without echo")

    args = parser.parse_args()

    admin_pwd = args.admin_password
    student_pwd = args.student_password

    if args.interactive:
        print("\n--- Interactive Demo Account Setup ---")
        admin_pwd = getpass.getpass(f"Enter password for Demo Admin ({DEMO_ADMIN_USERNAME}) [leave blank for default]: ").strip() or None
        student_pwd = getpass.getpass(f"Enter password for Demo Student ({DEMO_STUDENT_USERNAME}) [leave blank for default]: ").strip() or None

    print("=" * 65)
    print("   AI-BASED STUDENT PERFORMANCE PREDICTION — DEMO SETUP   ")
    print("=" * 65)
    print(f"[*] Target Demo Admin:   {DEMO_ADMIN_USERNAME}")
    print(f"[*] Target Demo Student: {DEMO_STUDENT_USERNAME} (linked to: {DEMO_STUDENT_ID})")
    print("[*] Provisioning accounts...")

    try:
        res = provision_demo_accounts(admin_password=admin_pwd, student_password=student_pwd)
        print("\n[+] SUCCESS: Demo accounts provisioned successfully!")
        print(f"    - Admin Account:   username='{res['admin']['username']}' (Action: {res['admin']['action']})")
        print(f"    - Student Account: username='{res['student']['username']}' (Action: {res['student']['action']})")
        print(f"    - Linked Profile:  student_id='{res['student']['linked_student_id']}'")
        print("\n[+] Security Note: Passwords are encrypted with PBKDF2/SHA-256 and never logged.")
        print("=" * 65)
        sys.exit(0)
    except Exception as e:
        print(f"\n[-] ERROR: Failed to provision demo accounts: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
