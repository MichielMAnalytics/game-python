#!/usr/bin/env python3
"""
Script to list all users and their data from the users database.
This is useful for debugging and administration purposes.
"""

import os
import sys
import sqlite3
import json
from tabulate import tabulate
from datetime import datetime
import hashlib
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Add the parent directory to sys.path if needed
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import functions from database.py
from database import get_db_connection, get_encryption_key, get_cipher

# Load environment variables
load_dotenv()

def format_datetime(timestamp):
    """Format a timestamp into a readable date/time format"""
    if not timestamp:
        return "N/A"
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return timestamp

def mask_token(token):
    """Mask the entire token for security purposes"""
    if not token:
        return "N/A"
    
    # Only show token type and nothing else
    if token.startswith("apx-"):
        return "[TWITTER-APX-TOKEN]"
    else:
        return "[ENCRYPTED-TOKEN]"

def mask_password_hash(password_hash):
    """Mask the password hash for security purposes"""
    if not password_hash:
        return "N/A"
    
    # Show that password is set, but mask the actual hash
    if ":" in password_hash:
        salt, hash_part = password_hash.split(":", 1)
        return f"[HASHED-PASSWORD:salt={salt[:5]}...]"
    
    return "[INVALID-HASH-FORMAT]"

def list_users(show_tokens=False, admin_mode=False):
    """List all users in the database with their data"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all user records with all fields
    cursor.execute('''
    SELECT user_id, email, password_hash, encrypted_token, encrypted_api_key, 
           user_info, created_at, updated_at, last_login, 
           reset_token, reset_token_expires
    FROM users
    ORDER BY updated_at DESC
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("No users found in the database.")
        return
    
    # Prepare data for display
    users_data = []
    cipher = get_cipher()
    
    for row in rows:
        user_id, email, password_hash, encrypted_token, encrypted_api_key, user_info_json, created_at, updated_at, last_login, reset_token, reset_token_expires = row
        
        # Token handling
        token = "[TWITTER-APX-TOKEN]"
        if show_tokens and admin_mode and encrypted_token and cipher:
            try:
                token = cipher.decrypt(encrypted_token.encode()).decode()
            except:
                token = "[DECRYPTION-FAILED]"
        
        # API Key handling
        api_key_status = "Not Set"
        if encrypted_api_key:
            api_key_status = "✓ Set"
            if show_tokens and admin_mode and cipher:
                try:
                    api_key = cipher.decrypt(encrypted_api_key.encode()).decode()
                    api_key_status = f"✓ {api_key[:5]}..."
                except:
                    api_key_status = "✓ [DECRYPTION-FAILED]"
        
        # Password hash handling
        password_status = mask_password_hash(password_hash)
        
        # Reset token status
        reset_status = "No"
        if reset_token:
            if reset_token_expires:
                try:
                    expires = datetime.fromisoformat(reset_token_expires.replace('Z', '+00:00'))
                    if datetime.now() > expires:
                        reset_status = "Expired"
                    else:
                        reset_status = "Active"
                except:
                    reset_status = "Invalid date"
            else:
                reset_status = "Active (no expiry)"
        
        # Parse user info
        twitter_handle = "N/A"
        twitter_id = "N/A"
        
        if user_info_json:
            try:
                info = json.loads(user_info_json)
                twitter_id = info.get('id', 'N/A')
                twitter_handle = info.get('name', 'N/A')
            except:
                pass
        
        # Format dates
        created = format_datetime(created_at)
        updated = format_datetime(updated_at)
        last_login_formatted = format_datetime(last_login)
        
        users_data.append([
            user_id, 
            email or "N/A",
            password_status,
            token,
            api_key_status,
            twitter_handle,
            twitter_id,
            reset_status,
            created,
            updated,
            last_login_formatted
        ])
    
    # Display the data
    headers = ["User ID", "Email", "Password", "Access Token", "API Key", 
               "Twitter Name", "Twitter ID", "Reset", "Created", "Updated", "Last Login"]
    print(tabulate(users_data, headers=headers, tablefmt="grid"))
    print(f"\nTotal users: {len(rows)}")

def show_database_info():
    """Show general information about the database"""
    db_path = os.path.join(os.path.dirname(__file__), 'users.db')
    
    if not os.path.exists(db_path):
        print(f"Database file not found at: {db_path}")
        return
    
    size = os.path.getsize(db_path)
    modified = datetime.fromtimestamp(os.path.getmtime(db_path))
    
    print(f"Database file: {db_path}")
    print(f"Size: {size/1024:.2f} KB")
    print(f"Last modified: {modified.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get encryption key info
    key = get_encryption_key()
    print(f"Encryption key: {'Present' if key else 'Missing'}")
    
    # Show database structure
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    conn.close()
    
    print("\nDatabase Structure:")
    column_data = []
    for col in columns:
        column_data.append([col[0], col[1], col[2], "YES" if col[3] else "NO", col[4], "YES" if col[5] else "NO"])
    
    print(tabulate(column_data, headers=["ID", "Name", "Type", "NotNull", "Default", "PK"], tablefmt="simple"))
    print("")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="List users from the tokens database")
    parser.add_argument("--show-tokens", action="store_true", 
                        help="Show full access tokens (extreme security risk, requires admin mode)")
    parser.add_argument("--admin", action="store_true", 
                        help="Enable admin mode for viewing sensitive information")
    args = parser.parse_args()
    
    # Warn about security risks if showing tokens
    if args.show_tokens:
        if not args.admin:
            print("ERROR: --show-tokens flag can only be used with --admin mode")
            sys.exit(1)
        else:
            print("\n⚠️  WARNING: SHOWING PLAINTEXT TOKENS IS A SECURITY RISK ⚠️")
            print("Only proceed if you are in a secure environment and need the actual tokens for debugging\n")
            response = input("Are you sure you want to continue? (yes/NO): ")
            if response.lower() != 'yes':
                print("Exiting without showing sensitive data.")
                sys.exit(0)
    
    show_database_info()
    list_users(show_tokens=args.show_tokens, admin_mode=args.admin) 