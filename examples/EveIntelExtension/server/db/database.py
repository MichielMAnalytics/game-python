import os
import sqlite3
import json
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import base64
import sys
import hashlib
import uuid
import secrets
import string
import re
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

def get_encryption_key():
    """Get the Fernet encryption key from environment variables"""
    key = os.getenv('FERNET_KEY')
    if not key:
        print("ERROR: FERNET_KEY environment variable not found!")
        print("Please run 'python db/generate_key.py' to create an encryption key")
        print("and add it to your .env file")
        return None
    
    # Convert string key back to bytes if needed
    if isinstance(key, str):
        key = key.encode()
    
    return key

def get_cipher():
    """Get a configured Fernet cipher object"""
    key = get_encryption_key()
    if not key:
        return None
    return Fernet(key)

def init_db():
    """Initialize the database schema"""
    db_path = os.path.join(os.path.dirname(__file__), 'users.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # First, check if the table already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    table_exists = cursor.fetchone() is not None
    
    if table_exists:
        # If the table exists, try to update it with new columns
        try:
            # Check if email column exists
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Add email column if it doesn't exist
            if 'email' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN email TEXT UNIQUE")
            
            # Add password_hash column if it doesn't exist
            if 'password_hash' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
                
            # Add last_login column if it doesn't exist
            if 'last_login' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN last_login TIMESTAMP")
                
            # Add reset_token column for password resets if it doesn't exist
            if 'reset_token' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN reset_token TEXT")
                
            # Add reset_token_expires column if it doesn't exist
            if 'reset_token_expires' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN reset_token_expires TIMESTAMP")
                
        except sqlite3.OperationalError as e:
            print(f"Warning: Could not alter table: {e}")
    else:
        # Create the table from scratch with all needed columns
        cursor.execute('''
        CREATE TABLE users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            password_hash TEXT,
            encrypted_token TEXT,
            encrypted_api_key TEXT,
            user_info TEXT,
            reset_token TEXT,
            reset_token_expires TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
        ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Get a connection to the SQLite database"""
    db_path = os.path.join(os.path.dirname(__file__), 'users.db')
    return sqlite3.connect(db_path)

def store_token(user_id, access_token, user_info=None):
    """Store an encrypted token for a user"""
    cipher = get_cipher()
    if not cipher:
        return False
    
    # Encrypt the token
    encrypted_token = cipher.encrypt(access_token.encode()).decode()
    
    # Prepare user info JSON
    user_info_json = None
    if user_info:
        user_info_json = json.dumps(user_info)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if user already exists
    cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    user_exists = cursor.fetchone() is not None
    
    if user_exists:
        # Update existing user
        update_query = 'UPDATE users SET encrypted_token = ?, updated_at = CURRENT_TIMESTAMP'
        params = [encrypted_token, user_id]
        
        if user_info_json:
            update_query += ', user_info = ?'
            params.insert(1, user_info_json)
        
        update_query += ' WHERE user_id = ?'
        cursor.execute(update_query, params)
    else:
        # Insert new user
        cursor.execute('''
        INSERT INTO users (user_id, encrypted_token, user_info, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, encrypted_token, user_info_json))
    
    conn.commit()
    conn.close()
    
    return True

def get_token(user_id):
    """Get a decrypted token for a user"""
    cipher = get_cipher()
    if not cipher:
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT encrypted_token FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result or result[0] is None:
        return None
    
    encrypted_token = result[0]
    try:
        decrypted_token = cipher.decrypt(encrypted_token.encode()).decode()
        return decrypted_token
    except Exception as e:
        print(f"Error decrypting token: {e}")
        return None

def get_user_info(user_id):
    """Get user info for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_info FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result or not result[0]:
        return None
    
    try:
        user_info = json.loads(result[0])
        return user_info
    except:
        return None

def update_user_info(user_id, user_info):
    """Update user info for an existing user"""
    if not user_info:
        return False
    
    user_info_json = json.dumps(user_info)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    UPDATE users SET user_info = ?, updated_at = CURRENT_TIMESTAMP
    WHERE user_id = ?
    ''', (user_info_json, user_id))
    
    conn.commit()
    conn.close()
    
    return cursor.rowcount > 0

def remove_token(user_id):
    """Mark a user as logged out without removing tokens"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # We'll keep the tokens but update the last logout time
    # This way, tokens are preserved but we can track logout status
    cursor.execute('''
    UPDATE users 
    SET updated_at = CURRENT_TIMESTAMP
    WHERE user_id = ?
    ''', (user_id,))
    
    result = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return result

def store_api_key(user_id, api_key):
    """Store an encrypted API key for a user"""
    cipher = get_cipher()
    if not cipher:
        return False
    
    # Encrypt the API key
    encrypted_api_key = cipher.encrypt(api_key.encode()).decode()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # First check if the user already exists
        cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        user_exists = cursor.fetchone() is not None
        
        if user_exists:
            # Update existing user
            cursor.execute('''
            UPDATE users 
            SET encrypted_api_key = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            ''', (encrypted_api_key, user_id))
        else:
            # Insert new user with just the API key
            cursor.execute('''
            INSERT INTO users (user_id, encrypted_api_key, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, encrypted_api_key))
        
        conn.commit()
        result = True
    except Exception as e:
        print(f"Error storing API key: {e}")
        conn.rollback()
        result = False
    finally:
        conn.close()
    
    return result

def get_api_key(user_id):
    """Get a decrypted API key for a user"""
    cipher = get_cipher()
    if not cipher:
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT encrypted_api_key FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result or result[0] is None:
        return None
    
    encrypted_api_key = result[0]
    try:
        decrypted_api_key = cipher.decrypt(encrypted_api_key.encode()).decode()
        return decrypted_api_key
    except Exception as e:
        print(f"Error decrypting API key: {e}")
        return None

def hash_password(password, salt=None):
    """Hash a password with salt using SHA-256"""
    if salt is None:
        # Generate a random salt
        salt = uuid.uuid4().hex
    
    # Hash the password with the salt
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    
    # Return both the salt and the hashed password
    return f"{salt}:{hashed}"

def verify_password(stored_password, provided_password):
    """Verify a password against its stored hash"""
    if not stored_password or ":" not in stored_password:
        print(f"Invalid stored password format: {stored_password}")
        return False
    
    try:
        # Split the stored password into salt and hash
        salt, stored_hash = stored_password.split(":", 1)
        
        # Hash the provided password with the same salt
        hash_to_check = hashlib.sha256((provided_password + salt).encode()).hexdigest()
        
        # Compare the hashes
        result = secrets.compare_digest(stored_hash, hash_to_check)
        print(f"Password verification: salt={salt[:5]}..., result={result}")
        return result
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False

def register_user(email, password):
    """Register a new user with email and password"""
    # Validate email format
    email = email.lower().strip()
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        print(f"Invalid email format: {email}")
        return None, "Invalid email format"
    
    # Generate a unique user ID first
    user_id = f"user-{uuid.uuid4()}"
    
    # Hash the password
    password_hash = hash_password(password)
    
    print(f"Attempting to register: email={email}, user_id={user_id}")
    print(f"Password hash format: {password_hash[:15]}...")
    
    # Open connection and create transaction
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # First check if email already exists
        cursor.execute('SELECT user_id FROM users WHERE email = ?', (email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            print(f"Email already registered: {email}")
            conn.close()
            return None, "Email already registered"
        
        # Debug: show all existing users before insert
        cursor.execute('SELECT user_id, email FROM users')
        existing_users = cursor.fetchall()
        print(f"Existing users before insert: {existing_users}")
        
        # Insert the new user
        cursor.execute('''
        INSERT INTO users (user_id, email, password_hash, created_at, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (user_id, email, password_hash))
        
        # Get row count to verify insert worked
        row_count = cursor.rowcount
        print(f"Insert affected {row_count} rows")
        
        # Verify the insert worked by querying for the new user
        cursor.execute('SELECT user_id, email FROM users WHERE user_id = ?', (user_id,))
        inserted_user = cursor.fetchone()
        print(f"Inserted user verification: {inserted_user}")
        
        # Commit the transaction
        conn.commit()
        
        # Final verification
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        print(f"Total users after insert: {total_users}")
        
        # Close the connection
        conn.close()
        
        if not inserted_user:
            print(f"WARNING: Insert appeared to succeed but user not found!")
            return None, "Registration failed - database error"
            
        return user_id, None
        
    except Exception as e:
        # Roll back on error
        conn.rollback()
        print(f"ERROR during registration: {str(e)}")
        conn.close()
        return None, str(e)

def login_user(email, password):
    """Authenticate a user with email and password"""
    # Normalize email
    email = email.lower().strip()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Print debugging info
    print(f"Attempting login for email: {email}")
    
    cursor.execute('SELECT user_id, password_hash, email FROM users WHERE email = ?', (email,))
    result = cursor.fetchone()
    
    if not result:
        print(f"No user found with email: {email}")
        conn.close()
        return None, "Email not found"
    
    user_id, stored_password, db_email = result
    print(f"Found user: {user_id}, Email from DB: {db_email}")
    
    # Check if the password hash is valid
    if not stored_password or ":" not in stored_password:
        print(f"Invalid password hash format for user {user_id}")
        conn.close()
        return None, "Invalid password storage format. Please reset your password."
    
    # Verify the password
    password_verified = verify_password(stored_password, password)
    print(f"Password verification result: {password_verified}")
    
    if not password_verified:
        conn.close()
        return None, "Invalid password"
    
    # Update last login timestamp
    cursor.execute('''
    UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?
    ''', (user_id,))
    
    conn.commit()
    conn.close()
    
    return user_id, None

def generate_secure_password(length=12):
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

# Add password reset functionality
def generate_reset_token(email):
    """Generate a password reset token for a user"""
    email = email.lower().strip()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id FROM users WHERE email = ?', (email,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return None, "Email not found"
    
    user_id = result[0]
    
    # Generate a random token
    reset_token = secrets.token_urlsafe(32)
    
    # Set expiration time (24 hours from now)
    expires = datetime.now() + timedelta(hours=24)
    expires_str = expires.isoformat()
    
    # Save token to database
    cursor.execute('''
    UPDATE users 
    SET reset_token = ?, reset_token_expires = ?
    WHERE user_id = ?
    ''', (reset_token, expires_str, user_id))
    
    conn.commit()
    conn.close()
    
    return reset_token, None

def reset_password(reset_token, new_password):
    """Reset a user's password using a reset token"""
    if not reset_token or len(new_password) < 8:
        return False, "Invalid token or password too short"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if token exists and is not expired
    cursor.execute('''
    SELECT user_id, reset_token_expires FROM users 
    WHERE reset_token = ?
    ''', (reset_token,))
    
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return False, "Invalid token"
    
    user_id, expires_str = result
    
    if expires_str:
        # Check if token is expired
        expires = datetime.fromisoformat(expires_str)
        if datetime.now() > expires:
            conn.close()
            return False, "Token expired"
    
    # Hash the new password
    password_hash = hash_password(new_password)
    
    # Update password and clear reset token
    cursor.execute('''
    UPDATE users 
    SET password_hash = ?, reset_token = NULL, reset_token_expires = NULL, updated_at = CURRENT_TIMESTAMP
    WHERE user_id = ?
    ''', (password_hash, user_id))
    
    conn.commit()
    conn.close()
    
    return True, None

def debug_users():
    """Print all users in the database for debugging"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT user_id, email, password_hash, 
           encrypted_token, encrypted_api_key,
           created_at, updated_at, last_login
    FROM users
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    print(f"\n===== DEBUG: FOUND {len(rows)} USERS =====")
    
    for row in rows:
        user_id, email, password_hash, encrypted_token, encrypted_api_key, created_at, updated_at, last_login = row
        
        # Mask sensitive data but show format
        if password_hash and ":" in password_hash:
            salt, _ = password_hash.split(":", 1)
            password_display = f"HASH:[salt={salt[:5]}...]"
        else:
            password_display = "INVALID_FORMAT"
        
        token_status = "SET" if encrypted_token else "NOT_SET"
        api_key_status = "SET" if encrypted_api_key else "NOT_SET"
        
        print(f"User: {user_id}")
        print(f"  Email: {email}")
        print(f"  Password: {password_display}")
        print(f"  Token: {token_status}")
        print(f"  API Key: {api_key_status}")
        print(f"  Created: {created_at}")
        print(f"  Updated: {updated_at}")
        print(f"  Last Login: {last_login}")
        print("-" * 50)
    
    print("======================================\n")

def check_database_integrity():
    """Check database structure and integrity"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("\n=== DATABASE INTEGRITY CHECK ===")
    
    try:
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("ERROR: Users table does not exist!")
            return False
        
        # Check table structure
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        required_columns = ['user_id', 'email', 'password_hash', 'encrypted_token', 
                           'encrypted_api_key', 'user_info', 'created_at', 'updated_at']
        
        missing_columns = [col for col in required_columns if col not in column_names]
        if missing_columns:
            print(f"WARNING: Missing columns in users table: {missing_columns}")
        
        # Check for unique constraint on email
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'")
        table_def = cursor.fetchone()[0]
        if 'UNIQUE' not in table_def and 'email' in table_def:
            print("WARNING: Email column may not have UNIQUE constraint!")
        
        # Check for orphaned records
        cursor.execute("SELECT COUNT(*) FROM users WHERE email IS NULL")
        null_emails = cursor.fetchone()[0]
        if null_emails > 0:
            print(f"WARNING: Found {null_emails} users with NULL email")
        
        # Check for foreign key integrity
        cursor.execute("PRAGMA foreign_key_check")
        fk_violations = cursor.fetchall()
        if fk_violations:
            print(f"WARNING: Foreign key violations found: {fk_violations}")
        
        print("Database integrity check completed.")
        return True
    
    except Exception as e:
        print(f"Error during database integrity check: {e}")
        return False
    finally:
        conn.close()

def check_user_auth_status(user_id):
    """Check if user has API key and Twitter token"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT email, encrypted_api_key, encrypted_token, user_info
    FROM users WHERE user_id = ?
    ''', (user_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return {
            'user_exists': False,
            'email': None,
            'has_api_key': False,
            'has_token': False,
            'has_user_info': False
        }
    
    email, encrypted_api_key, encrypted_token, user_info = result
    
    return {
        'user_exists': True,
        'email': email,
        'has_api_key': encrypted_api_key is not None,
        'has_token': encrypted_token is not None,
        'has_user_info': user_info is not None
    }

# Initialize the database when this module is imported
try:
    init_db()
    check_database_integrity()
except Exception as e:
    print(f"Error initializing database: {e}") 