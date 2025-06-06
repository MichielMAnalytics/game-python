#!/usr/bin/env python3
"""
Script to check if the FERNET_KEY is properly set up and working.
"""

import os
import sys
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Add the parent directory to sys.path if needed
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import from database.py
from database import get_encryption_key, get_cipher

# Load environment variables
load_dotenv()

def check_key():
    """Verify that the FERNET_KEY is valid and working correctly"""
    print("Checking FERNET_KEY...")
    
    # Get the raw key from environment
    raw_key = os.getenv('FERNET_KEY')
    if not raw_key:
        print("❌ ERROR: FERNET_KEY not found in environment variables")
        print("   Please run 'python db/generate_key.py' to create a key")
        return False
    
    # Check if the key has quotes
    if (raw_key.startswith('"') and raw_key.endswith('"')) or (raw_key.startswith("'") and raw_key.endswith("'")):
        print("⚠️  WARNING: Key contains quotes which may cause issues")
        print("   Raw key:", raw_key)
        print("   Please run 'python db/generate_key.py --fix' to remove quotes")
    else:
        print("✓ Key format looks good (no surrounding quotes)")
    
    # Get the processed key using our utility function
    key = get_encryption_key()
    if not key:
        print("❌ ERROR: Failed to process encryption key")
        return False
    
    # Try to create a cipher
    try:
        cipher = get_cipher()
        if not cipher:
            print("❌ ERROR: Failed to create Fernet cipher")
            return False
        
        # Test encryption and decryption
        test_data = "test_string"
        encrypted = cipher.encrypt(test_data.encode()).decode()
        decrypted = cipher.decrypt(encrypted.encode()).decode()
        
        if decrypted == test_data:
            print("✓ Encryption test passed!")
            return True
        else:
            print("❌ ERROR: Encryption test failed - decrypted data doesn't match original")
            return False
    
    except Exception as e:
        print(f"❌ ERROR: Exception during encryption test: {str(e)}")
        return False

if __name__ == "__main__":
    success = check_key()
    if success:
        print("\n✅ Your encryption key is correctly set up and working!")
    else:
        print("\n❌ There are issues with your encryption key configuration.")
        print("   Please fix the issues above to ensure secure token storage.") 