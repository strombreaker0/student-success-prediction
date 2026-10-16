"""
Administrator Account Creation Utility.
Safely bootstraps the primary administrator account without hardcoding default passwords.
Supports interactive entry or CLI flags.
"""

import sys
import argparse
import getpass
from src.db.connection import get_db_connection
from src.db.schema import create_schema
from src.services.auth_service import register_user, validate_password_strength


def create_admin_cli():
    parser = argparse.ArgumentParser(description="Create an administrator account.")
    parser.add_argument("--username", help="Admin username", default=None)
    parser.add_argument("--email", help="Admin email address", default=None)
    parser.add_argument("--name", help="Full name of administrator", default=None)
    parser.add_argument("--password", help="Admin password (or enter interactively)", default=None)
    args = parser.parse_args()

    print("=" * 65)
    print("  ADMINISTRATOR ACCOUNT SETUP  ")
    print("=" * 65)

    conn = get_db_connection()
    create_schema(conn)

    username = args.username
    if not username:
        username = input("Enter admin username [e.g. admin]: ").strip()

    email = args.email
    if not email:
        email = input("Enter admin email address [e.g. admin@institution.edu]: ").strip()

    name = args.name
    if not name:
        name = input("Enter administrator full name [e.g. Academic Administrator]: ").strip()

    password = args.password
    if not password:
        while True:
            pwd1 = getpass.getpass("Enter secure password (min 8 chars, 1 letter, 1 digit): ")
            ok, msg = validate_password_strength(pwd1)
            if not ok:
                print(f"  [!] {msg}")
                continue
            pwd2 = getpass.getpass("Confirm password: ")
            if pwd1 != pwd2:
                print("  [!] Passwords do not match. Please try again.")
                continue
            password = pwd1
            break

    success, msg, user = register_user(
        username=username,
        email=email,
        password=password,
        role="admin",
        full_name=name,
        conn=conn
    )

    if success:
        print(f"\n[+] Administrator '{username}' registered successfully!")
        print(f"    Email: {email}")
        print(f"    Role:  admin")
        print("[+] You may now log in to the web application.\n")
    else:
        print(f"\n[!] Failed to create administrator: {msg}\n")
        sys.exit(1)

    conn.close()


if __name__ == "__main__":
    create_admin_cli()
